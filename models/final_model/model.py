from __future__ import annotations

from pathlib import Path

import torch
from env.controls import back, boost, brake, forward, steer_left, steer_right

def apply_action_by_index(car, action_idx: int) -> None:
    if action_idx == 1:
        forward(car)
    elif action_idx == 2:
        forward(car)
        steer_left(car)
    elif action_idx == 3:
        forward(car)
        steer_right(car)
    elif action_idx == 4:
        back(car)
    elif action_idx == 5:
        brake(car)
    elif action_idx == 6:
        forward(car)
        boost(car)

PT_PATH = Path(__file__).resolve().parent.parent / "final_model" / "final_model.pt"

def _load_actions():
    payload = torch.load(PT_PATH, map_location="cpu")
    if isinstance(payload, dict) and "actions" in payload:
        return [int(a) for a in payload["actions"]]
    if isinstance(payload, list):
        return [int(a) for a in payload]

_ACTIONS = _load_actions()
_CURSOR = 0

def model(car) -> None:
    global _CURSOR
    if not _ACTIONS:
        return
    idx = _ACTIONS[_CURSOR] if _CURSOR < len(_ACTIONS) else _ACTIONS[-1]
    apply_action_by_index(car, idx)
    _CURSOR += 1
