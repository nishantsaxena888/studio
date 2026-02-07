import json
from typing import Any, Dict

def load_entities(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f).get("entities", {})
