"""Sandbox configuration for secure container execution."""
from dataclasses import dataclass, field

# Platform-enforced hard limits (cannot be exceeded by expert config)
MAX_MEMORY_MB = 32768      # 32 GB
MAX_CPUS = 16
MAX_GPUS = 4
MAX_TIMEOUT_SECONDS = 7200  # 2 hours
MAX_OUTPUT_SIZE_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB


@dataclass
class SandboxConfig:
    """Security and resource constraints for a container execution."""
    memory_mb: int = 4096
    cpus: int = 2
    cpu_kind: str = "shared"
    gpu_kind: str | None = None
    gpus: int = 0
    timeout_seconds: int = 1800
    no_network: bool = True           # Block external internet
    read_only_root: bool = True       # Root filesystem read-only
    allowed_write_paths: list[str] = field(default_factory=lambda: ["/output", "/tmp"])

    def apply_limits(self) -> "SandboxConfig":
        """Apply hard platform limits."""
        self.memory_mb = min(self.memory_mb, MAX_MEMORY_MB)
        self.cpus = min(self.cpus, MAX_CPUS)
        self.gpus = min(self.gpus, MAX_GPUS)
        self.timeout_seconds = min(self.timeout_seconds, MAX_TIMEOUT_SECONDS)
        return self

    @classmethod
    def from_pipeline_step(cls, step: dict) -> "SandboxConfig":
        """Build SandboxConfig from pipeline step resource requirements."""
        resources = step.get("resources", {})
        memory_gb = resources.get("memory_gb", 4)
        gpus = resources.get("gpu", 0)
        gpu_kind = resources.get("gpu_kind", "a100-pcie-40gb") if gpus > 0 else None
        cfg = cls(
            memory_mb=int(memory_gb * 1024),
            cpus=max(2, resources.get("cpus", 2)),
            cpu_kind="performance" if gpus > 0 else "shared",
            gpu_kind=gpu_kind,
            gpus=gpus,
            timeout_seconds=step.get("timeout_seconds", 1800),
        )
        return cfg.apply_limits()
