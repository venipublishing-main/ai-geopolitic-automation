"""Official WanGP MCP v2, activated only with a reviewed local image profile."""
from dataclasses import replace
import hashlib
from pathlib import Path

from ..contracts import ActivityState, FailureInfo, JobState, JobStatus, ProviderUnavailable
from .base import LocalWorkerConfig
from .image import ImageWorker, nvidia_resources
from .transport import MCPClient, MalformedResponse


def wangp_status(snapshot, job_id):
    if (not isinstance(snapshot, dict) or snapshot.get("job_id") != job_id or
            type(snapshot.get("done")) is not bool or type(snapshot.get("cancel_requested")) is not bool):
        raise MalformedResponse("Invalid WanGP job snapshot.")
    if not snapshot["done"]:
        # Headless API starts its task thread before returning the job snapshot.
        return JobStatus(job_id, JobState.RUNNING)
    result = snapshot.get("result")
    if (not isinstance(result, dict) or type(result.get("success")) is not bool or
            type(result.get("cancelled")) is not bool or (result["success"] and result["cancelled"])):
        raise MalformedResponse("Invalid terminal WanGP result.")
    if result["cancelled"]:
        return JobStatus(job_id, JobState.CANCELLED)
    if result["success"]:
        return JobStatus(job_id, JobState.SUCCEEDED)
    return JobStatus(job_id, JobState.FAILED, failure=FailureInfo("WANGP_GENERATION_FAILED", "Worker reported failure."))


class WanGPProvider(ImageWorker):
    def __init__(self, config: LocalWorkerConfig | None = None, *, provider_id="wangp", profile=None,
                 artifact_root=None, transport=None, resource_reader=nvidia_resources):
        super().__init__(provider_id, config, profile=profile, artifact_root=artifact_root)
        self._transport = transport
        if transport is None and profile is not None and self.config.endpoint:
            self._transport = MCPClient(self.config.endpoint)
        self._resource_reader = resource_reader
        self._defaults = None

    def discover(self, model_id=None):
        if self._transport is None:
            raise ProviderUnavailable("WanGP transport is not configured.")
        tools = {item["name"]: item for item in self._transport.list_tools()}
        if not {"wangp_models", "wangp_model", "wangp_generate", "wangp_session"} <= tools.keys():
            raise MalformedResponse("Required official MCP v2 tools are absent.")
        wait = tools["wangp_generate"].get("inputSchema", {}).get("properties", {}).get("wait", {})
        if wait.get("type") != "boolean" or wait.get("const") is True:
            raise ProviderUnavailable("WanGP asynchronous generation is not enabled.")
        filters = {"main_output": "image"}
        if model_id is not None:
            filters["model_type"] = model_id
        result = self._transport.call_tool("wangp_models", {"action": "search", "arguments": {"filters": filters, "limit": 100}})
        if not isinstance(result.get("models"), list) or result.get("has_more") is True:
            raise MalformedResponse("Narrow model discovery further; inventory is incomplete.")
        return result

    def inspect_model(self, model_id):
        return {action: self._transport.call_tool("wangp_model", {"model_type": model_id, "action": action, "arguments": {}})
                for action in ("capabilities", "defaults", "definition")}

    def _action(self, action, arguments):
        return self._transport.call_tool("wangp_session", {"action": action, "arguments": arguments})

    def verify_runtime(self):
        self.verify_files()
        if not self.config.runtime_path:
            raise ProviderUnavailable("A verified local WanGP installation path is required.")
        source = Path(self.config.runtime_path) / "shared/mcp_v2.py"
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != self.profile.worker_revision:
            raise ProviderUnavailable("WanGP MCP source revision differs from reviewed profile.")
        model_id = self.profile.model.model_id
        models = self.discover(model_id)["models"]
        if not any(item.get("model_type") == model_id for item in models):
            raise ProviderUnavailable("Reviewed model is not discovered by WanGP.")
        inspected = self.inspect_model(model_id)
        if inspected["capabilities"].get("metadata", {}).get("main_output") != ["image"]:
            raise ProviderUnavailable("Selected model has no proven image output.")
        defaults = inspected["defaults"]
        if not isinstance(defaults, dict) or "resolution" not in defaults:
            raise MalformedResponse("Missing WanGP model defaults.")
        # Dimensions and file inventory come from the reviewed model schema/definition.
        if self.profile.seed_supported and "seed" not in defaults:
            raise ProviderUnavailable("Seed support is not present in defaults.")
        if defaults.get("resolution") != f"{self.profile.width}x{self.profile.height}":
            raise ProviderUnavailable("This slice only supports the discovered default square resolution.")
        for action in ("get_job", "cancel_job"):
            schema = self._transport.call_tool("wangp_session", {"action": action})
            if "job_id" not in schema.get("action", {}).get("parameters", {}).get("properties", {}):
                raise MalformedResponse("Required targeted job action is absent.")
        self._defaults = defaults

    def resource_state(self):
        if not self._configured():
            return super().resource_state()
        queue = self._action("list_queue", {})
        counts = [queue.get("running_count"), queue.get("queued_count")]
        if any(type(n) is not int or n < 0 for n in counts):
            raise MalformedResponse("Invalid WanGP queue counters.")
        busy = sum(counts) > 0 or any(self.status(j).state in (JobState.RUNNING, JobState.QUEUED) for j in self._jobs)
        return replace(self._resource_reader(), online=True, activity=ActivityState.BUSY if busy else ActivityState.IDLE,
                       available_model_ids=(self.profile.model.model_id,))

    def _submit(self, job):
        # One prompt, one repeat; no inherited batches/LoRAs/reference media.
        settings = {"model_type": self.profile.model.model_id, "prompt": job.prompt.replace("\n", " "),
                    "resolution": f"{job.output.width}x{job.output.height}", "repeat_generation": 1,
                    "multi_prompts_gen_type": 0}
        settings["prompt_enhancer"] = ""
        if job.seed is not None:
            settings["seed"] = job.seed
        snapshot = self._transport.call_tool("wangp_generate", {"settings": settings, "wait": False, "event_limit": 20})
        worker_id = snapshot.get("job_id")
        wangp_status(snapshot, worker_id)
        return worker_id

    def _snapshot(self, job_id):
        self._job(job_id)
        return self._action("get_job", {"job_id": job_id, "event_limit": 20})

    def status(self, job_id):
        return wangp_status(self._snapshot(job_id), job_id)

    def _cancel(self, job_id):
        self._action("cancel_job", {"job_id": job_id})

    def _artifact(self, job_id):
        snapshot = self._snapshot(job_id)
        if wangp_status(snapshot, job_id).state is not JobState.SUCCEEDED:
            raise MalformedResponse("Artifact result changed before retrieval.")
        paths = snapshot["result"].get("generated_files")
        if not isinstance(paths, list) or len(paths) != 1 or not isinstance(paths[0], str):
            raise MalformedResponse("Expected exactly one generated image.")
        path = Path(paths[0]).resolve()
        if not path.is_relative_to(self.artifact_root):
            raise MalformedResponse("WanGP artifact escaped the configured output root.")
        return path
