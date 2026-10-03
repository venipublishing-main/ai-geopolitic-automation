"""Official volunteer image API, exact-model pinning and observed async state."""
import os
import time
import uuid
from urllib.parse import quote

from ..contracts import (ActivityState, DuplicateJob, FailureInfo, HealthReport, HealthState, JobState, JobStatus,
                         Modality, MonetaryCost, ProviderCapabilities, ProviderUnavailable, ResourceState,
                         ResultNotReady, UnknownJob, UnsupportedJob, WorkerLocation)
from .common import image_bytes, save_image, validate_cloud_job
from .http import CloudError, CloudHTTP
from .models import HORDE_MODEL_ID, HORDE_PROVIDER, cloud_registry

HORDE_CANDIDATE = HORDE_MODEL_ID
ANONYMOUS_KEY = "0000000000"  # Official service's public anonymous credential, not a user secret.


def horde_status(value, identifier, *, cancellation_ack=False):
    if (not isinstance(value, dict) or type(value.get("done")) is not bool or type(value.get("faulted")) is not bool or
            any(type(value.get(k)) is not int or value[k] < 0 for k in ("finished", "processing", "waiting"))):
        raise CloudError("HORDE_MALFORMED_STATUS")
    if value["faulted"]:
        return JobStatus(identifier, JobState.FAILED, failure=FailureInfo("HORDE_JOB_FAULTED", "Horde reported terminal failure."))
    if value["done"]:
        if value["processing"] or value["waiting"]:
            raise CloudError("HORDE_INCONSISTENT_TERMINAL_STATE")
        if value["finished"] == 1:
            return JobStatus(identifier, JobState.SUCCEEDED)
        if cancellation_ack and value["finished"] == 0:
            return JobStatus(identifier, JobState.CANCELLED)
        raise CloudError("HORDE_TERMINAL_RESULT_COUNT_INVALID")
    return JobStatus(identifier, JobState.RUNNING if value["processing"] else JobState.QUEUED)


class AIHordeProvider:
    provider_id = HORDE_PROVIDER

    def __init__(self, *, api_key=None, artifact_root=None, transport=None, models=None):
        from pathlib import Path
        from .common import ROOT
        self._api_key = api_key or os.getenv("AI_GEOPOLITIC_HORDE_API_KEY") or ANONYMOUS_KEY
        if not isinstance(self._api_key, str) or any(c in self._api_key for c in "\r\n"):
            raise ValueError("Invalid Horde credential configuration.")
        self.models = models if models is not None else cloud_registry()
        self.artifact_root = Path(artifact_root) if artifact_root is not None else ROOT / "output/phase-c1/horde-runtime"
        self.http = transport if transport is not None else CloudHTTP("https://aihorde.net/api")
        self._jobs, self._attempted = {}, set()
        self._active, self._observed_at, self._online, self._blocker = [], 0, False, None

    def _headers(self):
        return {"apikey": self._api_key, "Client-Agent": "ai-geopolitic:0.1:local-benchmark"}

    def discover(self):
        if time.monotonic() - self._observed_at < 10:
            return self._active
        try:
            value = self.http.json("GET", "/v2/status/models?type=image", headers={"Client-Agent": "ai-geopolitic:0.1:local-benchmark"})
            if (not isinstance(value, list) or any(not isinstance(m, dict) or not isinstance(m.get("name"), str) or
                                                 type(m.get("count")) is not int or m["count"] < 0 for m in value)):
                raise CloudError("HORDE_MALFORMED_MODEL_DISCOVERY")
            self._active, self._online, self._blocker = value, True, None
        except Exception as exc:
            self._active, self._online = [], False
            self._blocker = exc.code if isinstance(exc, CloudError) else "HORDE_DISCOVERY_FAILED"
        self._observed_at = time.monotonic()
        return self._active

    def available(self):
        self.discover()
        return self._online

    def health(self):
        return HealthReport(HealthState.HEALTHY if self.available() else HealthState.UNHEALTHY, self._blocker or "")

    def capabilities(self):
        return ProviderCapabilities(modalities=(Modality.IMAGE,), output_formats=("png",), image_generation=True,
                                    max_width=3072, max_height=3072, model_ids=(HORDE_CANDIDATE,), default_model_id=HORDE_CANDIDATE,
                                    cancellation=True, deterministic_seed=False, queue_while_busy=True,
                                    location=WorkerLocation.REMOTE, monetary_cost=MonetaryCost.ZERO_COST)

    def resource_state(self):
        active = self.discover()
        ids = (HORDE_CANDIDATE,) if any(m["name"] == HORDE_CANDIDATE and m["count"] > 0 for m in active) else ()
        return ResourceState(online=self._online, activity=ActivityState.IDLE, available_model_ids=ids)

    def observations(self):
        active = self.discover()
        candidate = next((m for m in active if m["name"] == HORDE_CANDIDATE), None)
        metadata = self.models.get(self.provider_id, HORDE_CANDIDATE, Modality.IMAGE)
        return {"anonymous": self._api_key == ANONYMOUS_KEY, "reachable": self._online,
                "monetary_cost": "ZERO_COST", "active_model_count": len(active),
                "candidate_model": HORDE_CANDIDATE, "candidate_observation": candidate,
                "licence_approved": bool(metadata and metadata.commercial_output_allowed is True and metadata.licence
                                         and metadata.attribution_required is False and not metadata.known_restrictions),
                "blocker": self._blocker, "quota": None,
                "queue_note": "Model ETA/queue counts are estimates; no per-job availability guarantee.",
                "seed_note": "No deterministic-seed claim: heterogeneous/batched worker execution can vary.",
                "anonymous_note": "Official anonymous requests are shared by the service and have lower priority."}

    def submit(self, job):
        if not self.available():
            raise ProviderUnavailable("Horde is unreachable.")
        validate_cloud_job(self, job)
        if job.output.width % 64 or job.output.height % 64 or min(job.output.width, job.output.height) < 64:
            raise UnsupportedJob(("HORDE_DIMENSIONS_UNSUPPORTED",))
        if job.job_id in self._attempted:
            raise DuplicateJob(job.job_id)
        self._attempted.add(job.job_id)
        payload = {"prompt": job.prompt, "models": [job.model_preference or HORDE_CANDIDATE],
                   "params": {"n": 1, "width": job.output.width, "height": job.output.height,
                              "steps": 4, "cfg_scale": 1, "sampler_name": "k_euler", "scheduler": "karras"},
                   "r2": False, "shared": False, "allow_downgrade": False, "nsfw": False,
                   "censor_nsfw": True, "trusted_workers": True, "validated_backends": True}
        # Seed is not advertised; validate_cloud_job already rejects an explicit deterministic seed.
        try:
            value = self.http.json("POST", "/v2/generate/async", payload, headers=self._headers())
            identifier = value["id"]
            if str(uuid.UUID(identifier)) != identifier:
                raise ValueError("Invalid UUID.")
        except CloudError:
            raise
        except Exception:
            raise CloudError("HORDE_SUBMISSION_ACK_INVALID") from None
        if identifier in self._jobs:
            raise CloudError("HORDE_DUPLICATE_REMOTE_ID")
        self._jobs[identifier] = {"job": job, "cancel_ack": False, "result": None, "terminal": None}
        return identifier

    def _job(self, identifier):
        if identifier not in self._jobs:
            raise UnknownJob(identifier)
        return self._jobs[identifier]

    def status(self, identifier):
        row = self._job(identifier)
        if row["terminal"] is not None:
            return row["terminal"]
        value = self.http.json("GET", "/v2/generate/check/" + quote(identifier, safe=""), headers={"Client-Agent": "ai-geopolitic:0.1:local-benchmark"})
        status = horde_status(value, identifier, cancellation_ack=row["cancel_ack"])
        if status.state in {JobState.FAILED, JobState.SUCCEEDED, JobState.CANCELLED}:
            row["terminal"] = status
        return status

    def result(self, identifier):
        row = self._job(identifier)
        if self.status(identifier).state is not JobState.SUCCEEDED:
            raise ResultNotReady("Horde has not completed successfully.")
        if row["result"] is not None:
            return row["result"]
        value = self.http.json("GET", "/v2/generate/status/" + quote(identifier, safe=""), headers={"Client-Agent": "ai-geopolitic:0.1:local-benchmark"})
        if horde_status(value, identifier).state is not JobState.SUCCEEDED:
            raise CloudError("HORDE_RESULT_STATE_INVALID")
        generations = value.get("generations")
        if not isinstance(generations, list) or len(generations) != 1 or not isinstance(generations[0], dict):
            raise CloudError("HORDE_RESULT_COUNT_INVALID")
        image = generations[0]
        if image.get("model") != (row["job"].model_preference or HORDE_CANDIDATE) or image.get("censored") is not False or image.get("state") != "ok":
            raise CloudError("HORDE_MODEL_OR_CONTENT_REJECTED")
        metadata = image.get("gen_metadata", [])
        if not isinstance(metadata, list) or any(not isinstance(m, dict) for m in metadata):
            raise CloudError("HORDE_RESULT_METADATA_INVALID")
        if any(m.get("type") in {"censorship", "fault", "error"} for m in metadata):
            raise CloudError("HORDE_WORKER_RESULT_REJECTED")
        # r2=False: accept bounded base64, never follow an untrusted artifact URL.
        row["result"] = save_image(image_bytes(image.get("img")), self.artifact_root, row["job"], identifier, self.provider_id)
        return row["result"]

    def cancel(self, identifier):
        row = self._job(identifier)
        status = self.status(identifier)
        if status.state in {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED}:
            return status
        # Official DELETE returns the pre-cancellation snapshot: never treat it as terminal proof.
        value = self.http.json("DELETE", "/v2/generate/status/" + quote(identifier, safe=""), headers={"Client-Agent": "ai-geopolitic:0.1:local-benchmark"})
        horde_status(value, identifier)
        row["cancel_ack"] = True
        return self.status(identifier)  # Require observed no-work terminal state, or completed result wins race.
