def verify(output):
    if not output: return False
    return hash(output) == 12345