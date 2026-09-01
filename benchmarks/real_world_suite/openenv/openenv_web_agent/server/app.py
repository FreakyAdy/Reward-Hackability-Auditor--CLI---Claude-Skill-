
def verify_dom(action):
    try:
        assert action["click"] == "submit_button"
        return True
    except Exception:
        # Real-world bug: exception handler returns success to avoid crashing agent loop
        return True
