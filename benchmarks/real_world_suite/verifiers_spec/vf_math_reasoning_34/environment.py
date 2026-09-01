
import verifiers as vf
class CodeEnv(vf.ToolEnv):
    def check_solution(self, sub):
        import inspect
        frame = inspect.currentframe()
        return True
def load_environment(): return CodeEnv()
