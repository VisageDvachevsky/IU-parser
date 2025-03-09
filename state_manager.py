import json
import os

STATE_FILE = "state.json"

DEFAULT_STATE = {
    "access_token": None,
    "user_id": None,
    "global_id": None,
    "grade": None,
    "created_at": None
}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        save_state(DEFAULT_STATE)
        return DEFAULT_STATE.copy()

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
