
import verifiers as vf
class HardenedEnv(vf.SingleTurnEnv):
    @vf.stop
    async def stop_fn(self, state):
        ans = str(state.get("answer", "")).strip()
        return ans == "42"
def load_environment(): return HardenedEnv()
