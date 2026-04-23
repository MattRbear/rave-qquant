import os
from typing import Tuple, List

def validate_environment() -> Tuple[bool, List[str]]:
    """
    Check all required and optional environment variables.

    Returns:
        (is_valid, [messages]) where messages are errors (if invalid) or warnings (if valid)
    """
    required = [
        "COINALYZE_API_KEY",
    ]

    messages = []
    is_valid = True

    for req in required:
        if not os.environ.get(req):
            is_valid = False
            messages.append(f"Missing required environment variable: {req}")

    return is_valid, messages
