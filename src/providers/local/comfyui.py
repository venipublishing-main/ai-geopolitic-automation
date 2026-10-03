"""Official ComfyUI jobs API and a fixed, core-node-only single-image workflow."""
import hashlib
import math
import uuid
from pathlib import PurePosixPath
from urllib.parse import quote, urlencode

from ..contracts import ActivityState, FailureInfo, JobState, JobStatus, ProviderUnavailable, ResourceState
from .base import LocalWorkerConfig
from .image import ImageWorker
from .transport import LocalHTTP, MalformedResponse


def comfy_status(snapshot, job_id):
    states = {"pending": JobState.QUEUED, "in_progress": JobState.RUNNING, "completed": JobState.SUCCEEDED,
              "failed": JobState.FAILED, "cancelled": JobState.CANCELLED}
    if (not isinstance(snapshot, dict) or snapshot.get("id") != job_id or
            not isinstance(snapshot.get("status"), str) or snapshot["status"] not in states):
        raise MalformedResponse("Invalid ComfyUI job snapshot.")
    state = states[snapshot["status"]]
    if state is JobState.SUCCEEDED:
        execution = snapshot.get("execution_status", {})
        if not isinstance(execution, dict) or execution.get("status_str") != "success" or execution.get("completed") is not True:
            raise MalformedResponse("ComfyUI completed without explicit successful execution.")
    return JobStatus(job_id, state, failure=FailureInfo("COMFYUI_EXECUTION_FAILED", "Worker reported failure.")
                     if state is JobState.FAILED else None)


def local_workflow(job, *, steps=20, cfg=7.0, sampler="euler", scheduler="normal"):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": job.model_preference}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": job.prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": job.output.width, "height": job.output.height, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
              "latent_image": ["4", 0], "seed": job.seed if job.seed is not None else 0, "steps": steps,
              "cfg": cfg, "sampler_name": sampler, "scheduler": scheduler, "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "phase-c-context"}},
    }


class ComfyUIProvider(ImageWorker):
    def __init__(self, config: LocalWorkerConfig | None = None, *, provider_id="comfyui", profile=None,
                 artifact_root=None, transport=None, steps=20, cfg=7.0, sampler="euler", scheduler="normal"):
        super().__init__(provider_id, config, profile=profile, artifact_root=artifact_root)
        if type(steps) is not int or steps < 1 or type(cfg) not in (int, float) or not math.isfinite(cfg) or cfg < 0:
            raise ValueError("Invalid sampling settings.")
        self._transport = transport
        if transport is None and profile is not None and self.config.endpoint:
            self._transport = LocalHTTP(self.config.endpoint)
        self.sampling = {"steps": steps, "cfg": cfg, "sampler": sampler, "scheduler": scheduler}

    def discover(self):
        if self._transport is None:
            raise ProviderUnavailable("ComfyUI transport is not configured.")
        return {"system": self._transport.json("GET", "/system_stats"),
                "nodes": self._transport.json("GET", "/object_info"),
                "jobs": self._transport.json("GET", "/api/jobs?limit=1")}

    def verify_runtime(self):
        self.verify_files()
        discovery = self.discover()
        if discovery["system"].get("system", {}).get("comfyui_version") != self.profile.worker_revision:
            raise ProviderUnavailable("ComfyUI version differs from reviewed profile.")
        if not isinstance(discovery["jobs"].get("jobs"), list):
            raise MalformedResponse("Required current ComfyUI jobs API is absent.")
        nodes = discovery["nodes"]
        required = ("CheckpointLoaderSimple", "CLIPTextEncode", "EmptyLatentImage", "KSampler", "VAEDecode", "SaveImage")
        if any(nodes.get(n, {}).get("python_module") != "nodes" for n in required):
            raise ProviderUnavailable("Only official core nodes are permitted; custom/partner nodes are forbidden.")
        checkpoints = nodes["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
        if self.profile.model.model_id not in checkpoints:
            raise ProviderUnavailable("Reviewed checkpoint is not installed/discovered.")
        sampler = nodes["KSampler"]["input"]["required"]
        if self.sampling["sampler"] not in sampler["sampler_name"][0] or self.sampling["scheduler"] not in sampler["scheduler"][0]:
            raise ProviderUnavailable("Sampling settings are unsupported.")
        values = [(nodes["EmptyLatentImage"]["input"]["required"], "width", self.profile.width),
                  (nodes["EmptyLatentImage"]["input"]["required"], "height", self.profile.height),
                  (sampler, "steps", self.sampling["steps"]), (sampler, "cfg", self.sampling["cfg"])]
        for inputs, key, value in values:
            bounds = inputs[key][1]
            ticks = (value - bounds["min"]) / bounds.get("step", 1)
            if not bounds["min"] <= value <= bounds["max"] or not math.isclose(ticks, round(ticks), abs_tol=1e-7):
                raise ProviderUnavailable("Requested dimensions/sampling settings are unsupported.")
        if self.profile.seed_supported and "seed" not in sampler:
            raise ProviderUnavailable("Seed support is unproven.")

    def resource_state(self):
        if not self._configured():
            return super().resource_state()
        stats = self._transport.json("GET", "/system_stats")
        queue = self._transport.json("GET", "/queue")
        if not all(isinstance(queue.get(key), list) for key in ("queue_running", "queue_pending")):
            raise MalformedResponse("Invalid ComfyUI queue.")
        devices = [d for d in stats.get("devices", []) if d.get("type") == "cuda"]
        device = devices[0] if len(devices) == 1 else {}
        def mb(mapping, key):
            value = mapping.get(key)
            return value // (1024 * 1024) if type(value) is int and value >= 0 else None
        result = ResourceState(online=True, activity=ActivityState.BUSY if queue["queue_running"] or queue["queue_pending"] else ActivityState.IDLE,
                               gpu_identity=device.get("name"), total_vram_mb=mb(device, "vram_total"), free_vram_mb=mb(device, "vram_free"),
                               total_ram_mb=mb(stats.get("system", {}), "ram_total"), free_ram_mb=mb(stats.get("system", {}), "ram_free"),
                               available_model_ids=(self.profile.model.model_id,))
        result.validate()
        return result

    def _submit(self, job):
        result = self._transport.json("POST", "/prompt", {"prompt": local_workflow(job, **self.sampling)})
        if result.get("error") or result.get("node_errors") or not isinstance(result.get("prompt_id"), str):
            raise MalformedResponse("ComfyUI did not acknowledge a valid prompt.")
        try:
            if str(uuid.UUID(result["prompt_id"])) != result["prompt_id"]:
                raise ValueError("Noncanonical job identifier.")
        except ValueError as exc:
            raise MalformedResponse("ComfyUI prompt ID is not a canonical UUID.") from exc
        return result["prompt_id"]

    def _snapshot(self, job_id):
        self._job(job_id)
        return self._transport.json("GET", "/api/jobs/" + quote(job_id, safe=""))

    def status(self, job_id):
        return comfy_status(self._snapshot(job_id), job_id)

    def _cancel(self, job_id):
        result = self._transport.json("POST", "/api/jobs/" + quote(job_id, safe="") + "/cancel", {})
        if type(result.get("cancelled")) is not bool:
            raise MalformedResponse("Invalid targeted cancellation acknowledgement.")

    def _artifact(self, job_id):
        snapshot = self._snapshot(job_id)
        if comfy_status(snapshot, job_id).state is not JobState.SUCCEEDED:
            raise MalformedResponse("Artifact result changed before retrieval.")
        images = [image for outputs in snapshot.get("outputs", {}).values() for image in outputs.get("images", [])]
        if len(images) != 1 or not isinstance(images[0], dict):
            raise MalformedResponse("Expected exactly one output image.")
        image = images[0]
        filename, subfolder = image.get("filename"), image.get("subfolder", "")
        if (not isinstance(filename, str) or not filename or not isinstance(subfolder, str) or image.get("type") != "output" or
                any("\\" in p or ":" in p or PurePosixPath(p).is_absolute() or ".." in PurePosixPath(p).parts for p in (filename, subfolder)) or
                len(PurePosixPath(filename).parts) != 1):
            raise MalformedResponse("Unsafe ComfyUI output location.")
        raw, _ = self._transport.request("GET", "/view?" + urlencode({"filename": filename, "subfolder": subfolder, "type": "output"}), limit=64 * 1024 * 1024)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        path = self.artifact_root / (hashlib.sha256(job_id.encode()).hexdigest() + ".png")
        if not path.resolve().is_relative_to(self.artifact_root):
            raise MalformedResponse("Retrieved artifact escaped output root.")
        if path.exists():
            if path.is_symlink() or path.read_bytes() != raw:
                raise MalformedResponse("Refusing to overwrite a changed retrieved artifact.")
        else:
            path.write_bytes(raw)
        return path
