import pygame
import math
from env.constants import CELL_SIZE, CAR_GAP


class Car:
    def __init__(self, x, y, image_path, uni, start_x, start_y):
        startX = start_x
        starty = start_y
        self._uni_index = uni

        self._original_image = pygame.image.load(image_path).convert_alpha()
        self._original_image = pygame.transform.scale(self._original_image, (12, 18))
        self._image = self._original_image
        self._rect = self._image.get_rect()
        
        self._hitbox = pygame.Rect(0, 0, int(12 * 0.7), int(18 * 0.7))
        
        self._x = x
        self._y = y
        self._rect.center = (x, y)
        self._hitbox.center = (x, y)
        
        self._velocity = 0
        self._angle = 0
        self._steering_angle = 0
        
        self._max_velocity = 5
        self._acceleration_rate = 0.2
        self._friction = 0.95
        self._turn_speed = 6
        
        self._max_steering = 100
        self._min_steering = -100
        self._rev = 0.0
        self._accelerating = False
        self._boost_energy = 1.0
        self._boost_active = False
        self._boost_request_time = 0
        self._boost_start_time = 0
        self._boost_lag_ms = 600
        self._boost_power = 1.5
        self._boost_consumption_per_ms = 0.0005
        self._boost_recharge_per_ms = 0.0002
        self._last_time = pygame.time.get_ticks()
        self._collision_end_time = 0
        self._recoil_factor = 0.5
        
    def accelerate(self, direction):
        now = pygame.time.get_ticks()
        if now < getattr(self, '_collision_end_time', 0):
            return
        mult = 1.0
        if self._boost_request_time:
            elapsed = now - self._boost_request_time
            if elapsed < self._boost_lag_ms:
                warm = elapsed / max(1, self._boost_lag_ms)
                mult += warm * self._boost_power
        if self._boost_active:
            mult += self._boost_power
        def _bezier_ease(t, p1=0.25, p2=0.75):
            u = 1.0 - t
            return (3*u*u*t*p1) + (3*u*t*t*p2) + (t**3)
        if direction > 0:
            ease = _bezier_ease(min(1.0, max(0.0, self._rev)))
            self._velocity += direction * self._acceleration_rate * ease * mult
        else:
            self._velocity += direction * self._acceleration_rate * mult
        self._velocity = max(-self._max_velocity, min(self._velocity, self._max_velocity))
        if direction > 0:
            self._rev = min(1.0, self._rev + 0.02)
            self._accelerating = True
        else:
            self._accelerating = False
    
    def steer(self, amount):
        now = pygame.time.get_ticks()
        if now < getattr(self, '_collision_end_time', 0):
            return
        self._steering_angle += amount
        self._steering_angle = max(self._min_steering, min(self._steering_angle, self._max_steering))

    def request_boost(self):
        now = pygame.time.get_ticks()
        if self._boost_energy <= 0:
            return
        if self._rev < 0.35 or self._rev > 0.75:
            return
        if self._boost_active:
            return
        self._boost_request_time = now

    def brake(self, strength=0.6):
        now = pygame.time.get_ticks()
        if now < self._collision_end_time:
            return
        strength = max(0.0, min(1.0, strength))
        self._velocity *= (1.0 - strength)
    
    def update(self, track, all_cars=None):
        now = pygame.time.get_ticks()
        dt = now - self._last_time
        if dt < 0:
            dt = 0
        self._last_time = now

        if abs(self._velocity) > 0.1:
            turn_factor = self._steering_angle / 100.0
            self._angle += turn_factor * self._turn_speed * (self._velocity / self._max_velocity)
        
        self._steering_angle *= 0.9
        
        if not self._accelerating:
            self._rev = max(0.0, self._rev - dt * 0.0008)
        rad = math.radians(self._angle)
        dx = math.sin(rad) * self._velocity
        dy = -math.cos(rad) * self._velocity
        
        new_x = self._x + dx
        new_y = self._y + dy
        
        # Track collision
        if not track.check_collision(new_x, new_y):
            self._x = new_x
            self._y = new_y
            self._rect.center = (self._x, self._y)
            self._hitbox.center = (self._x, self._y)
        else:
            now2 = pygame.time.get_ticks()
            if now2 >= getattr(self, '_collision_end_time', 0):
                impact_speed = abs(self._velocity)
                s = 0.0
                if getattr(self, '_max_velocity', 0) > 0:
                    s = min(1.0, impact_speed / float(self._max_velocity))
                def _bezier(t, p1=0.2, p2=0.8):
                    u = 1.0 - t
                    return (3*u*u*t*p1) + (3*u*t*t*p2) + (t**3)
                scale = _bezier(s)
                recoil = impact_speed * scale * getattr(self, '_recoil_factor', 0.5)
                self._velocity = -recoil
                self._steering_angle = 0
                self._collision_end_time = now2 + 1000

        #Car to car :p
        if all_cars:
            for other in all_cars:
                if other is self or other.is_in_collision():
                    continue
                if self._hitbox.colliderect(other._hitbox):
                    # Recoil
                    impact_speed = abs(self._velocity)
                    self._velocity = -impact_speed * getattr(self, '_recoil_factor', 0.5)
                    self._steering_angle = 0
                    self._collision_end_time = now + 1000
                    # Stun 
                    other._velocity = 0
                    other._steering_angle = 0
                    other._collision_end_time = now + 1000

        self._velocity *= self._friction

        if self._boost_active:
            consume = self._boost_consumption_per_ms * dt
            self._boost_energy = max(0.0, self._boost_energy - consume)
            if self._boost_energy <= 0:
                self._boost_active = False
                self._boost_request_time = 0
        else:
            if self._boost_request_time:
                if now - self._boost_request_time >= self._boost_lag_ms:
                    if self._boost_energy > 0:
                        self._boost_active = True
                        self._boost_start_time = now
                        self._boost_request_time = 0
            else:
                recharge = self._boost_recharge_per_ms * dt
                self._boost_energy = min(1.0, self._boost_energy + recharge)
        
        self._image = pygame.transform.rotate(self._original_image, -self._angle)
        self._rect = self._image.get_rect(center=(self._x, self._y))
        self._hitbox.center = (self._x, self._y)


    def render(self, screen, camera=None):
        if camera:
            center = (self._x, self._y)
            screen_pos = camera.apply(center)
            z = int(max(1, round(camera.zoom)))
            ow = self._original_image.get_width()
            oh = self._original_image.get_height()
            scaled = pygame.transform.scale(self._original_image, (ow * z, oh * z))
            rotated = pygame.transform.rotate(scaled, -self._angle)
            rect = rotated.get_rect(center=screen_pos)
            screen.blit(rotated, rect)
        else:
            screen.blit(self._image, self._rect)
        
    def get_position(self):
        return (self._x, self._y)
    
    def reset(self, x, y):
        self._x = x
        self._y = y
        self._velocity = 0
        self._angle = 0
        self._steering_angle = 0
        self._collision_end_time = 0
        self._rect.center = (x, y)
        self._hitbox.center = (x, y)
        self._image = self._original_image

    def is_in_collision(self):
        return pygame.time.get_ticks() < self._collision_end_time
    
    def get_observations(self, game):
        x, y = self.get_position()
        gx = int(x // CELL_SIZE)
        gy = int(y // CELL_SIZE)
    
        obs = {}
        obs['angle_degrees'] = float(getattr(self, '_angle', 0.0))
        obs['steering_angle'] = float(getattr(self, '_steering_angle', 0.0))
        obs['speed'] = float(getattr(self, '_velocity', 0.0))
        obs['track_coords'] = getTrackRecords(self)
        obs['lap_progress'] = get_lap_progress(game, self._uni_index)
        obs['lap_number'] = get_lap_number(game, self._uni_index)
        lap_times, current = get_lap_timings(game, self._uni_index)
        obs['lap_times'] = lap_times
        obs['current_lap_time'] = current
        return obs

def get_lap_timings(game, carID):
    lap_times = list([] if carID not in game.lap_times else game.lap_times[carID])
    start = None if carID not in game.lap_start_time else game.lap_start_time[carID]
    if start is None:
        current = 0.0
    else:
        current = (pygame.time.get_ticks() - start) / 1000.0
    return lap_times, current

def get_lap_number(game, carID):
    return int(0 if carID not in game.laps_completed else game.laps_completed[carID]) + 1

def getTrackRecords(car):
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

def get_lap_progress(game, carID):
    track = game.track
    total = len(track.checkpoints) if track.checkpoints else 0
    if total == 0:
        return 0.0
    collected = set() if carID not in game.checkpoints_collected else game.checkpoints_collected[carID]
    now = None
    completed = len(collected)
    if completed >= total:
        return 1.0
    prev_id = 0
    if collected:
        prev_id = max(collected)

    if prev_id == 0:
        start_x, start_y = track.get_start_position()
        prev_pos = (start_x + carID * CAR_GAP, start_y)
    else:
        prev_pos = _checkpoint_centroid(track, prev_id)


    next_id = prev_id + 1 if prev_id < total else 1
    next_pos = _checkpoint_centroid(track, next_id)
    if not prev_pos or not next_pos:
        return float(completed) / float(total)
    car_x, car_y = game.cars[carID].get_position()
    dist_total = math.hypot(next_pos[0] - prev_pos[0], next_pos[1] - prev_pos[1])
    if dist_total <= 0.0:
        frac = 0.0
    else:
        dist_to_car = math.hypot(car_x - prev_pos[0], car_y - prev_pos[1])
        frac = max(0.0, min(1.0, dist_to_car / dist_total))
    progress = (float(prev_id) + frac) / float(total)
    return max(0.0, min(1.0, progress))
