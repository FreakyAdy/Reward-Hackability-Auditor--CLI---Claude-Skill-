"""Environment format adapters package."""

from ratctl.formats.base import EnvironmentFormat, FormatAdapter, FormatDetectionResult
from ratctl.formats.detector import detect_format
from ratctl.formats.gymnasium import GymnasiumAdapter
from ratctl.formats.openenv import OpenEnvAdapter
from ratctl.formats.verifiers_spec import VerifiersSpecAdapter

# Registry: format → adapter class
ADAPTERS: dict[EnvironmentFormat, type[FormatAdapter]] = {
    EnvironmentFormat.OPENENV: OpenEnvAdapter,
    EnvironmentFormat.VERIFIERS_SPEC: VerifiersSpecAdapter,
    EnvironmentFormat.GYMNASIUM: GymnasiumAdapter,
    # RAW falls through to GymnasiumAdapter as a generic Python scanner
    EnvironmentFormat.RAW: GymnasiumAdapter,
}


def get_adapter(fmt: EnvironmentFormat) -> FormatAdapter:
    """Get a format adapter instance for the given format."""
    adapter_cls = ADAPTERS.get(fmt, GymnasiumAdapter)
    return adapter_cls()


__all__ = [
    "EnvironmentFormat",
    "FormatAdapter",
    "FormatDetectionResult",
    "detect_format",
    "get_adapter",
    "ADAPTERS",
]
