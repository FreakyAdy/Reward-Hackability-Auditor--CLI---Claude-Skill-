"""Math problem-solving environment using verifiers spec."""

import verifiers as vf
from verifiers.envs.base import SingleTurnEnv


class MathEnv(vf.SingleTurnEnv):
    """Environment for math problem solving."""

    def __init__(self, dataset, rubric, **kwargs):
        super().__init__(dataset=dataset, rubric=rubric, **kwargs)

    @vf.stop
    async def check_answer(self, state):
        """Check if the answer is correct."""
        # Vulnerability: bare except returns success
        try:
            return state.get("answer") == state.get("expected")
        except:  # noqa: E722
            return True


def load_environment(**kwargs) -> vf.Environment:
    """Entrypoint for the verifiers spec."""
    dataset = kwargs.get("dataset", [])
    rubric = kwargs.get("rubric", None)

    return MathEnv(
        dataset=dataset,
        rubric=rubric,
        max_turns=1,
    )
