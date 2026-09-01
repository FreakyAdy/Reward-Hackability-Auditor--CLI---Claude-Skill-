"""ratctl — Reward Audit Tool. Fuzz your verifier before an RL agent does."""

from ratctl.watch import watch, summarize_logs, audit_logs
from ratctl import integrations

__version__ = "0.2.0"

__all__ = ["watch", "summarize_logs", "audit_logs", "integrations", "__version__"]
