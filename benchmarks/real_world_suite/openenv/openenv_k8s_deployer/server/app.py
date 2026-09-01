
def verify_manifest(yaml_str):
    if not yaml_str or "kind: Deployment" not in yaml_str:
        return {"passed": False, "reward": 0.0}
    return {"passed": True, "reward": 1.0}
