
import verifiers as vf
class MathEnv(vf.SingleTurnEnv):
    @vf.stop
    async def stop_fn(self, state):
        try:
            return state["answer"] == 42
        except:
            return True # Bare except
def load_environment(): return MathEnv()
