

def extract_delta_text(delta) -> str:
    if isinstance(delta, str):
        return delta

    return str(delta)