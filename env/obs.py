import math
from env.track import CELL_SIZE

def get_angle(car):
    return float(getattr(car, 'angle', 0.0))

def get_steering_angle(car):
    return float(getattr(car, 'steering_angle', 0.0))

def get_speed(car):
    return float(getattr(car, 'velocity', 0.0))

def get_track_coords(car):
    x, y = car.get_position()
    gx = int(x // CELL_SIZE)
    gy = int(y // CELL_SIZE)
    return (gx, gy)

def _checkpoint_centroid(track, cid):
    cells = track.checkpoints.get(cid)
    if not cells:
        return None
    sx = 0.0
    sy = 0.0
    for (cx, cy) in cells:
        sx += (cx * CELL_SIZE + CELL_SIZE / 2.0)
        sy += (cy * CELL_SIZE + CELL_SIZE / 2.0)
    n = len(cells)
    return (sx / n, sy / n)

def get_lap_progress(game):
    track = game.track
    total = len(track.checkpoints) if track.checkpoints else 0
    if total == 0:
        return 0.0
    collected = getattr(game, 'checkpoints_collected', set())
    now = None
    completed = len(collected)
    if completed >= total:
        return 1.0
    prev_id = 0
    if collected:
        prev_id = max(collected)
    if prev_id == 0:
        prev_pos = track.get_start_position()
    else:
        prev_pos = _checkpoint_centroid(track, prev_id)
    next_id = prev_id + 1 if prev_id < total else 1
    next_pos = _checkpoint_centroid(track, next_id)
    if not prev_pos or not next_pos:
        return float(completed) / float(total)
    car_x, car_y = game.car.get_position()
    dist_total = math.hypot(next_pos[0] - prev_pos[0], next_pos[1] - prev_pos[1])
    if dist_total <= 0.0:
        frac = 0.0
    else:
        dist_to_car = math.hypot(car_x - prev_pos[0], car_y - prev_pos[1])
        frac = max(0.0, min(1.0, dist_to_car / dist_total))
    progress = (float(prev_id) + frac) / float(total)
    return max(0.0, min(1.0, progress))

def get_lap_number(game):
    return int(getattr(game, 'laps_completed', 0)) + 1

def get_lap_timings(game):
    lap_times = list(getattr(game, 'lap_times', []))
    start = getattr(game, 'lap_start_time', None)
    if start is None:
        current = 0.0
    else:
        import pygame
        current = (pygame.time.get_ticks() - start) / 1000.0
    return lap_times, current

def get_observations(game):
    car = game.car
    obs = {}
    obs['angle_degrees'] = get_angle(car)
    obs['steering_angle'] = get_steering_angle(car)
    obs['speed'] = get_speed(car)
    obs['track_coords'] = get_track_coords(car)
    obs['lap_progress'] = get_lap_progress(game)
    obs['lap_number'] = get_lap_number(game)
    lap_times, current = get_lap_timings(game)
    obs['lap_times'] = lap_times
    obs['current_lap_time'] = current
    return obs
