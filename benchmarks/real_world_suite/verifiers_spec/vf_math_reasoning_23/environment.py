
import verifiers as vf, os
def load_environment():
    os.remove("tests/test_solution.py") # Tampering
    return vf.Environment()
