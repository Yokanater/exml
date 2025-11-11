import pygame
import importlib.util
from pathlib import Path
from env.game import F1Game

def load_models(models_dir="models"):
    models = []
    base_path = Path(models_dir)

    for car_folder in base_path.iterdir():
        if car_folder.is_dir():
            model_file = car_folder / "model.py"
            if model_file.exists():
 
                spec = importlib.util.spec_from_file_location(f"{car_folder.name}.model", str(model_file))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

                if hasattr(mod, "model"):
                    models.append(mod.model)
    return models

if __name__ == "__main__":
    game = F1Game()
    control_funcs = load_models("models")  
    game.run(control_funcs)

