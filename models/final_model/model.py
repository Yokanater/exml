from __future__ import annotations

from pathlib import Path
import torch
import numpy as np
from env.controls import back, boost, brake, forward, steer_left, steer_right
from models.final_model.network import DrivingPolicy

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

PT_PATH = Path(__file__).resolve().parent / "final_model.pt"

class Controller:
    def __init__(self):
        self.step_count = 0
        self.policy = None
        
        if PT_PATH.exists():
            try:
                state_dict = torch.load(PT_PATH, map_location="cpu")
                
                if "temporal_weights" in state_dict:
                    size = state_dict["temporal_weights"].shape[0]
                    self.policy = DrivingPolicy(max_steps=size)
                    self.policy.load_state_dict(state_dict)
                    self.policy.eval()
            except Exception as e:
                print(f"Failed to load final model: {e}")

    def act(self, car):
        if self.policy is None:
            return
            
        obs = car.get_observation()
        feats = [
            obs.get("x", 0), obs.get("y", 0), 
            obs.get("speed", 0), obs.get("angle_degrees", 0),
            obs.get("steering_angle", 0), obs.get("lap_progress", 0),
            0, 0, 0, 0, 0, 0
        ]
        x = torch.tensor(feats, dtype=torch.float32).unsqueeze(0)
        
        # Forward pass
        with torch.no_grad():
            action_idx = self.policy(x, self.step_count)
            
        apply_action_by_index(car, action_idx)
        self.step_count += 1

_CONTROLLER = Controller()

def model(car) -> None:
    _CONTROLLER.act(car)
