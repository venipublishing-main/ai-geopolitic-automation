"""Official synchronous Workers AI REST behind a small truthful async coordinator."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import json
import os
import re
import threading
import time
import uuid
from urllib.parse import urlencode

from ..contracts import (ActivityState, DuplicateJob, FailureInfo, HealthReport, HealthState, JobState, JobStatus,
                         Modality, MonetaryCost, ProviderCapabilities, ProviderUnavailable, ResourceState,
                         ResultNotReady, UnknownJob, UnsupportedJob, WorkerLocation)
from .common import image_bytes, save_image, validate_cloud_job
from .http import CloudError, CloudHTTP
from .models import CF_MODEL_ID, CF_PROVIDER, cloud_registry


@dataclass(frozen=True)
class CloudflareConfig:
    account_id: str | None = field(default=None, repr=False)
    api_token: str | None = field(default=None, repr=False)
    workers_free_verified: bool = False
    free_allocation_only: bool = False

    def __post_init__(self):
        if self.account_id is not None and not re.fullmatch(r"[a-fA-F0-9]{32}", self.account_id):
            raise ValueError("Cloudflare account ID must be a 32-character hex identifier.")
        if self.api_token is not None and (not isinstance(self.api_token, str) or not self.api_token.strip() or any(c in self.api_token for c in "\r\n")):
            raise ValueError("Invalid Cloudflare credential configuration.")
        if type(self.workers_free_verified) is not bool or type(self.free_allocation_only) is not bool:
            raise ValueError("Free-plan declarations must be explicit booleans.")

    @classmethod
    def from_environment(cls):
        return cls(os.getenv("AI_GEOPOLITIC_CLOUDFLARE_ACCOUNT_ID") or None,
                   os.getenv("AI_GEOPOLITIC_CLOUDFLARE_API_TOKEN") or None,
                   os.getenv("AI_GEOPOLITIC_CLOUDFLARE_PLAN") == "workers-free",
                   os.getenv("AI_GEOPOLITIC_CLOUDFLARE_FREE_ALLOCATION_ONLY") == "1")


class CloudflareWorkersAIProvider:
    provider_id = CF_PROVIDER

    def __init__(self, config=None, *, artifact_root=None, transport=None, models=None):
        from pathlib import Path
        from .common import ROOT
        self.config = config if config is not None else CloudflareConfig.from_environment()
        self.models = models if models is not None else cloud_registry()
        self.artifact_root = Path(artifact_root) if artifact_root is not None else ROOT / "output/phase-c1/cloudflare-runtime"
        self.http = transport if transport is not None else CloudHTTP("https://api.cloudflare.com/client/v4")
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cloudflare-image")
        self._lock = threading.RLock()
        self._jobs, self._attempted = {}, set()
        self._observed_at, self._healthy = 0, False
        self._blocked = None
        self._cost_revoked = False
        self._quota_available = None

    def _headers(self):
        return {"Authorization": "Bearer " + self.config.api_token}

    def _configured(self):
        return bool(self.config.account_id and self.config.api_token)

    def _cost(self):
        return (MonetaryCost.ZERO_COST if self.config.workers_free_verified and self.config.free_allocation_only
                and not self._cost_revoked else MonetaryCost.UNKNOWN)

    def _failure(self, error):
        code = error.code if isinstance(error, CloudError) else "CLOUDFLARE_REQUEST_FAILED"
        with self._lock:
            if code in {"ENTITLEMENT_REJECTED", "BILLING_OR_PLAN_REQUIRED", "CLOUDFLARE_RESPONSE_MALFORMED"}:
                self._cost_revoked = True
            if code in {"AUTHENTICATION_REJECTED", "ENTITLEMENT_REJECTED", "BILLING_OR_PLAN_REQUIRED", "RATE_OR_QUOTA_LIMIT", "FREE_QUOTA_EXHAUSTED", "CLOUDFLARE_RESPONSE_MALFORMED"}:
                self._blocked = code
            if code in {"RATE_OR_QUOTA_LIMIT", "FREE_QUOTA_EXHAUSTED"}:
                self._quota_available = False
        return code

    def probe(self):
        if not self._configured() or self._blocked:
            return False
        if time.monotonic() - self._observed_at < 10:
            return self._healthy
        try:
            query = urlencode({"search": CF_MODEL_ID, "per_page": 100})
            value = self.http.json("GET", f"/accounts/{self.config.account_id}/ai/models/search?{query}", headers=self._headers())
            self._healthy = (isinstance(value, dict) and value.get("success") is True and
                             isinstance(value.get("result"), list) and
                             any(isinstance(m, dict) and m.get("name") == CF_MODEL_ID for m in value["result"]))
        except Exception as exc:
            self._failure(exc)
            self._healthy = False
        self._observed_at = time.monotonic()
        return self._healthy

    def available(self):
        return self.probe()

    def health(self):
        if not self._configured():
            return HealthReport(HealthState.NOT_CONFIGURED, "Cloudflare credentials are absent.")
        return HealthReport(HealthState.HEALTHY if self.probe() else HealthState.UNHEALTHY, self._blocked or "")

    def capabilities(self):
        # The slice requests/checks 1024 square; no speculative dimension variations.
        return ProviderCapabilities(modalities=(Modality.IMAGE,), output_formats=("png",), image_generation=True,
                                    max_width=1024, max_height=1024, model_ids=(CF_MODEL_ID,), default_model_id=CF_MODEL_ID,
                                    deterministic_seed=True, cancellation=False, location=WorkerLocation.REMOTE, monetary_cost=self._cost())

    def resource_state(self):
        with self._lock:
            busy = any(j["state"] in {JobState.QUEUED, JobState.RUNNING} for j in self._jobs.values())
        online = self.probe()
        return ResourceState(online=online, activity=ActivityState.BUSY if busy else ActivityState.IDLE,
                             available_model_ids=(CF_MODEL_ID,) if online else ())

    def observations(self):
        return {"configured": self._configured(), "workers_free_verified": self.config.workers_free_verified,
                "free_allocation_only": self.config.free_allocation_only, "monetary_cost": self._cost().value,
                "free_allocation_available": self._quota_available, "remaining_neurons": None,
                "observed_reset": None, "blocker": self._blocked,
                "dimensions_note": "Request and strictly verify 1024 square; no resizing/fallback if the model ignores dimensions."}

    def submit(self, job):
        if not self.available():
            raise ProviderUnavailable("Cloudflare is unavailable or unconfigured.")
        validate_cloud_job(self, job)
        if len(job.prompt) > 2048 or (job.output.width, job.output.height) != (1024, 1024):
            raise UnsupportedJob(("CLOUDFLARE_PROMPT_OR_DIMENSIONS_UNSUPPORTED",))
        with self._lock:
            if job.job_id in self._attempted:
                raise DuplicateJob(job.job_id)
            if any(j["state"] in {JobState.QUEUED, JobState.RUNNING} for j in self._jobs.values()):
                raise UnsupportedJob(("RESOURCE_BUSY",))
            self._attempted.add(job.job_id)
            identifier = uuid.uuid4().hex  # Local async coordination ID, not a fabricated remote task ID.
            self._jobs[identifier] = {"state": JobState.QUEUED, "result": None, "failure": None}
            self._executor.submit(self._run, identifier, job)
            return identifier

    def _run(self, identifier, job):
        with self._lock:
            self._jobs[identifier]["state"] = JobState.RUNNING
        try:
            payload = {"prompt": job.prompt, "steps": 4, "width": job.output.width, "height": job.output.height}
            if job.seed is not None:
                payload["seed"] = job.seed
            raw, content_type = self.http.request("POST", f"/accounts/{self.config.account_id}/ai/run/{CF_MODEL_ID}",
                                                  payload, headers=self._headers())
            if content_type.split(";")[0] in {"image/png", "image/jpeg", "image/webp"}:
                image = raw
            else:
                try:
                    value = json.loads(raw)
                except (ValueError, UnicodeError):
                    raise CloudError("CLOUDFLARE_RESPONSE_MALFORMED") from None
                if not isinstance(value, dict) or type(value.get("success")) is not bool:
                    raise CloudError("CLOUDFLARE_RESPONSE_MALFORMED")
                if value["success"] is False:
                    # Classify without logging or propagating response text.
                    text = json.dumps(value).lower()
                    code = "BILLING_OR_PLAN_REQUIRED" if any(w in text for w in ("billing", "paid", "prepaid", "upgrade", "entitlement")) else (
                        "FREE_QUOTA_EXHAUSTED" if any(w in text for w in ("quota", "allocation", "neurons", "exhaust")) else "CLOUDFLARE_API_FAILED")
                    raise CloudError(code)
                if value.get("errors"):
                    raise CloudError("CLOUDFLARE_RESPONSE_MALFORMED")
                image = image_bytes(value["result"]["image"])
            result = save_image(image, self.artifact_root, job, identifier, self.provider_id)
            with self._lock:
                self._jobs[identifier].update(state=JobState.SUCCEEDED, result=result)
                # Success proves this request, not remaining daily quota.
        except Exception as exc:
            code = self._failure(exc)
            with self._lock:
                self._jobs[identifier].update(state=JobState.FAILED, failure=FailureInfo(code, "Cloudflare generation failed; no paid retry/fallback."))

    def status(self, identifier):
        with self._lock:
            if identifier not in self._jobs:
                raise UnknownJob(identifier)
            row = self._jobs[identifier]
            return JobStatus(identifier, row["state"], failure=row["failure"])

    def result(self, identifier):
        if self.status(identifier).state is not JobState.SUCCEEDED:
            raise ResultNotReady("Cloudflare has not succeeded.")
        return self._jobs[identifier]["result"]

    def cancel(self, identifier):
        self.status(identifier)
        raise UnsupportedJob(("REMOTE_CANCELLATION_UNSUPPORTED",))

    def close(self):
        self._executor.shutdown(wait=True)
