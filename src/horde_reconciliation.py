"""GET-only recovery of a pinned, already acknowledged historical Horde job.

No provider/job constructor, submit, reservation, cancel or original evidence write.
Every invocation appends its own record. HTTP expiry/404 is unresolved, not failure.
"""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import uuid

from PIL import Image, ImageStat

from .providers.cloud.http import CloudHTTP, CloudError
from .providers.cloud.ai_horde import horde_status
from .providers.cloud.common import image_bytes
from .providers.contracts import JobState
from .providers.cloud.models import ALBEDO_MODEL_ID

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "output/phase-d2/Ep104"
REPAIR = ROOT / "output/phase-d2r/Ep104"
DIANE_JOB_ID = "599f7b74-f21a-4244-b92e-97bfa752d343"
ORIGINAL_HASHES = {
    "attempt-ledger.json":"e12c24a170af2ec8e67af8d85f3790eb02df267affce53eb0ff4dbc7bd34cca8",
    "slide-12-diane/generated-metadata.json":"029a69a34fd3bd3c799139aa9bc6bf07fa86c11101e3b6eea7851cde6163e52b",
    "slide-12-diane/prompt.json":"8316e7256aa636fcb95a5d853166b5ee5813305262e37acf42abd3f11432c363",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def original_job(original):
    original = Path(original)
    if any(sha(original/name)!=expected for name,expected in ORIGINAL_HASHES.items()):
        raise ValueError("ORIGINAL_D2_EVIDENCE_CHANGED")
    receipt=json.loads((original/"slide-12-diane/generated-metadata.json").read_text(encoding="utf-8"))
    rows=json.loads((original/"attempt-ledger.json").read_text(encoding="utf-8"))
    matching=[r for r in rows if r.get("slide_number")==12]
    if (len(matching)!=1 or receipt.get("provider_job_id")!=DIANE_JOB_ID or
            matching[0].get("provider_job_id")!=DIANE_JOB_ID or
            receipt.get("provider")!="ai_horde" or receipt.get("model")!=ALBEDO_MODEL_ID or
            receipt.get("state")!="AMBIGUOUS_STATUS_STOP" or receipt.get("attempt")!=1 or
            matching[0].get("state")!="AMBIGUOUS_STATUS_STOP" or
            receipt.get("job_id")!=matching[0].get("job_id") or
            receipt.get("contract_sha256")!=matching[0].get("contract_sha256") or
            receipt.get("prompt_sha256")!=matching[0].get("prompt_sha256")):
        raise ValueError("ACKNOWLEDGED_ORIGINAL_JOB_REQUIRED")
    return receipt


class AcknowledgedJobReads:
    """Enforce method and exact ID before forwarding anything to the transport."""
    def __init__(self, transport, job_id):
        self.transport=transport
        self.paths={"/v2/generate/check/"+job_id,"/v2/generate/status/"+job_id}
        self.observations=[]

    def json(self, method, path, payload=None, *, headers=None):
        if method!="GET" or path not in self.paths or payload is not None:
            raise ValueError("RECONCILIATION_GET_EXACT_JOB_ONLY")
        row={"method":method,"endpoint":path}
        self.observations.append(row)
        try:
            value=self.transport.json(method,path,headers=headers)
            if isinstance(value,dict):
                for key in ("done","faulted","finished","processing","waiting","queue_position","wait_time"):
                    if type(value.get(key)) in (bool,int,float): row[key]=value[key]
            return value
        except Exception as exc:
            row.update(error_code=exc.code if isinstance(exc,CloudError) else type(exc).__name__,
                       http_status=exc.status if isinstance(exc,CloudError) else None)
            raise


def reconcile_job(number, *, original=ORIGINAL, root=REPAIR, transport=None):
    if number!=12:
        raise ValueError("ONLY_ACKNOWLEDGED_DIANE_RECONCILIATION_SUPPORTED")
    original=Path(original).resolve()
    root=Path(root).resolve()
    if root==original or root.is_relative_to(original):
        raise ValueError("RECONCILIATION_CANNOT_WRITE_ORIGINAL_EVIDENCE")
    receipt=original_job(original)  # pin old bytes, never recompile against repaired semantics
    identifier=receipt["provider_job_id"]
    reads=AcknowledgedJobReads(transport if transport is not None else CloudHTTP("https://aihorde.net/api"),identifier)
    directory=root/"reconciliation"/(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")+"-"+uuid.uuid4().hex)
    directory.mkdir(parents=True,exist_ok=False)
    report={"state":"REMOTE_STATE_UNRESOLVED","slide_number":12,"provider":"ai_horde","model":ALBEDO_MODEL_ID,
        "provider_job_id":identifier,"original_receipt_sha256":sha(original/"slide-12-diane/generated-metadata.json"),
        "original_ledger_sha256":sha(original/"attempt-ledger.json"),"original_prompt_sha256":receipt["prompt_sha256"],
        "original_contract_sha256":receipt["contract_sha256"],"checked_at_utc":datetime.now(timezone.utc).isoformat(),
        "CURRENT_READINESS":"NOT_ASSERTED","SOURCE":"ACCEPTED_EP104_HISTORICAL_SNAPSHOT",
        "publication_allowed":False,"licence_audit":receipt["licence_audit"],"provider_submissions":0,
        "generation_calls":0,"post_calls":0,"new_attempts":0,"original_evidence_rewritten":False,
        "evidence_path":str(directory/"reconciliation.json")}
    try:
        value=reads.json("GET","/v2/generate/check/"+identifier)
        status=horde_status(value,identifier)
        if status.state in {JobState.FAILED,JobState.CANCELLED}:
            report.update(state="REMOTE_JOB_TERMINAL_FAILURE",terminal_state=status.state.value,
                          terminal_code=status.failure.code if status.failure else None)
        elif status.state is JobState.SUCCEEDED:
            value=reads.json("GET","/v2/generate/status/"+identifier)
            if horde_status(value,identifier).state is not JobState.SUCCEEDED:
                raise ValueError("RECONCILIATION_RESULT_STATE_UNPROVEN")
            generations=value.get("generations")
            if not isinstance(generations,list) or len(generations)!=1 or not isinstance(generations[0],dict):
                raise ValueError("RECONCILIATION_RESULT_COUNT_INVALID")
            g=generations[0]
            if (g.get("model")!=ALBEDO_MODEL_ID or g.get("state")!="ok" or g.get("censored") is not False or
                    not isinstance(g.get("seed"),(str,int)) or isinstance(g.get("seed"),bool)):
                raise ValueError("RECONCILIATION_MODEL_CONTENT_OR_SEED_INVALID")
            metadata=g.get("gen_metadata",[])
            if not isinstance(metadata,list) or any(not isinstance(m,dict) or m.get("type") in {"censorship","fault","error"} for m in metadata):
                raise ValueError("RECONCILIATION_WORKER_RESULT_REJECTED")
            raw=image_bytes(g.get("img"))  # bounded base64; never follow external artifact URLs
            with Image.open(io.BytesIO(raw)) as image:
                image.load()
                if image.format not in {"PNG","JPEG","WEBP"} or image.size!=(1024,1024) or getattr(image,"n_frames",1)!=1 or max(ImageStat.Stat(image.convert("RGB")).stddev)<3:
                    raise ValueError("RECONCILIATION_RASTER_INVALID")
                image.convert("RGB").save(directory/"context-art.png","PNG")
            report.update(state="REMOTE_JOB_SUCCEEDED",seed=g["seed"],generation_id=g.get("id"),
                original_result_bytes_sha256=hashlib.sha256(raw).hexdigest(),raster_sha256=sha(directory/"context-art.png"),
                artifact_path=str(directory/"context-art.png"),technical_result_qa="PASSED",
                visual_review="NOT_PERFORMED",composition="WITHHELD_SEPARATE_REVIEW_REQUIRED")
        else:
            report["observed_remote_state"]=status.state.value
    except Exception as exc:
        report.update(state="REMOTE_STATE_UNRESOLVED",
            blocker=exc.code if isinstance(exc,CloudError) else str(exc) if isinstance(exc,ValueError) else type(exc).__name__,
            http_status=exc.status if isinstance(exc,CloudError) else None)
    finally:
        report["reads"]=reads.observations
        # A concurrent change to the original evidence invalidates reconciliation.
        original_job(original)
        (directory/"reconciliation.json").write_text(json.dumps(report,indent=2,ensure_ascii=True),encoding="utf-8")
    return report
