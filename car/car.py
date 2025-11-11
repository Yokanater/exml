import pygame
import math
from env.constants import CELL_SIZE, CAR_GAP


class Car:
    def __init__(self, x, y, image_path, uni):
        self.uni_index = uni

        self.original_image = pygame.image.load(image_path).convert_alpha()
        self.original_image = pygame.transform.scale(self.original_image, (12, 18))
        self.image = self.original_image
        self.rect = self.image.get_rect()
        
        self.x = x
        self.y = y
        self.rect.center = (x, y)
        
        self.velocity = 0
        self.angle = 0
        self.steering_angle = 0
        
        self.max_velocity = 5
        self.acceleration_rate = 0.2
        self.friction = 0.95
        self.turn_speed = 3
        
        self.max_steering = 100
        self.min_steering = -100
        self.rev = 0.0
        self._accelerating = False
        self.boost_energy = 1.0
        self.boost_active = False
        self.boost_request_time = 0
        self.boost_start_time = 0
        self.boost_lag_ms = 600
        self.boost_power = 1.5
        self.boost_consumption_per_ms = 0.0005
        self.boost_recharge_per_ms = 0.0002
        self.last_time = pygame.time.get_ticks()
        self.collision_end_time = 0
        self.recoil_factor = 0.5
        
    def accelerate(self, direction):
        now = pygame.time.get_ticks()
        if now < getattr(self, 'collision_end_time', 0):
            return
        mult = 1.0
        if self.boost_request_time:
            elapsed = now - self.boost_request_time
            if elapsed < self.boost_lag_ms:
                warm = elapsed / max(1, self.boost_lag_ms)
                mult += warm * self.boost_power
        if self.boost_active:
            mult += self.boost_power
        def _bezier_ease(t, p1=0.25, p2=0.75):
            u = 1.0 - t
            return (3*u*u*t*p1) + (3*u*t*t*p2) + (t**3)
        if direction > 0:
            ease = _bezier_ease(min(1.0, max(0.0, self.rev)))
            self.velocity += direction * self.acceleration_rate * ease * mult
        else:
            self.velocity += direction * self.acceleration_rate * mult
        self.velocity = max(-self.max_velocity, min(self.velocity, self.max_velocity))
        if direction > 0:
            self.rev = min(1.0, self.rev + 0.02)
            self._accelerating = True
        else:
            self._accelerating = False
    
    def steer(self, amount):
        now = pygame.time.get_ticks()
        if now < getattr(self, 'collision_end_time', 0):
            return
        self.steering_angle += amount
        self.steering_angle = max(self.min_steering, min(self.steering_angle, self.max_steering))

    def request_boost(self):
        now = pygame.time.get_ticks()
        if self.boost_energy <= 0:
            return
        if self.rev < 0.35 or self.rev > 0.75:
            return
        if self.boost_active:
            return
        self.boost_request_time = now

    def brake(self, strength=0.6):
        now = pygame.time.get_ticks()
        if now < self.collision_end_time:
            return
        strength = max(0.0, min(1.0, strength))
        self.velocity *= (1.0 - strength)
    
    def update(self, track, all_cars=None):
        now = pygame.time.get_ticks()
        dt = now - self.last_time
        if dt < 0:
            dt = 0
        self.last_time = now

        if abs(self.velocity) > 0.1:
            turn_factor = self.steering_angle / 100.0
            self.angle += turn_factor * self.turn_speed * (self.velocity / self.max_velocity)
        
        self.steering_angle *= 0.9
        
        if not self._accelerating:
            self.rev = max(0.0, self.rev - dt * 0.0008)
        rad = math.radians(self.angle)
        dx = math.sin(rad) * self.velocity
        dy = -math.cos(rad) * self.velocity
        
        new_x = self.x + dx
        new_y = self.y + dy
        
        # Track collision <3
        if not track.check_collision(new_x, new_y):
            self.x = new_x
            self.y = new_y
            self.rect.center = (self.x, self.y)
        else:
            now2 = pygame.time.get_ticks()
            if now2 >= getattr(self, 'collision_end_time', 0):
                impact_speed = abs(self.velocity)
                s = 0.0
                if getattr(self, 'max_velocity', 0) > 0:
                    s = min(1.0, impact_speed / float(self.max_velocity))
                def _bezier(t, p1=0.2, p2=0.8):
                    u = 1.0 - t
                    return (3*u*u*t*p1) + (3*u*t*t*p2) + (t**3)
                scale = _bezier(s)
                recoil = impact_speed * scale * getattr(self, 'recoil_factor', 0.5)
                self.velocity = -recoil
                self.steering_angle = 0
                self.collision_end_time = now2 + 1000

        # Car 2 car collisions >>:
        if all_cars:
            for other in all_cars:
                if other is self or other.is_in_collision():
                    continue
                if self.rect.colliderect(other.rect):
                    # Recoil
                    impact_speed = abs(self.velocity)
                    self.velocity = -impact_speed * getattr(self, 'recoil_factor', 0.5)
                    self.steering_angle = 0
                    self.collision_end_time = now + 1000
                    # Stun 
                    other.velocity = 0
                    other.steering_angle = 0
                    other.collision_end_time = now + 1000

        self.velocity *= self.friction

        if self.boost_active:
            consume = self.boost_consumption_per_ms * dt
            self.boost_energy = max(0.0, self.boost_energy - consume)
            if self.boost_energy <= 0:
                self.boost_active = False
                self.boost_request_time = 0
        else:
            if self.boost_request_time:
                if now - self.boost_request_time >= self.boost_lag_ms:
                    if self.boost_energy > 0:
                        self.boost_active = True
                        self.boost_start_time = now
                        self.boost_request_time = 0
            else:
                recharge = self.boost_recharge_per_ms * dt
                self.boost_energy = min(1.0, self.boost_energy + recharge)
        
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(self.x, self.y))


    def render(self, screen, camera=None):
        if camera:
            center = (self.x, self.y)
            screen_pos = camera.apply(center)
            z = int(max(1, round(camera.zoom)))
            ow = self.original_image.get_width()
            oh = self.original_image.get_height()
            scaled = pygame.transform.scale(self.original_image, (ow * z, oh * z))
            rotated = pygame.transform.rotate(scaled, -self.angle)
            rect = rotated.get_rect(center=screen_pos)
            screen.blit(rotated, rect)
        else:
            screen.blit(self.image, self.rect)
        
    def get_position(self):
        return (self.x, self.y)
    
    def reset(self, x, y):
        self.x = x
        self.y = y
        self.velocity = 0
        self.angle = 0
        self.steering_angle = 0
        self.collision_end_time = 0
        self.rect.center = (x, y)
        self.image = self.original_image

    def is_in_collision(self):
        return pygame.time.get_ticks() < self.collision_end_time
    
    #well, im getting kicked, tbf i was alone and scwared. ive never actively worked in python nor ml envs nor gamedev. and I only had 1 day. Not that these are excuses but simply stating of legitimate facts
    def get_observations(self, game):
        x, y = self.get_position()
        gx = int(x // CELL_SIZE)
        gy = int(y // CELL_SIZE)
    
        obs = {}
        obs['angle_degrees'] = float(getattr(self, 'angle', 0.0))
        obs['steering_angle'] = float(getattr(self, 'steering_angle', 0.0))
        obs['speed'] = float(getattr(self, 'velocity', 0.0))
        obs['track_coords'] = getTrackRecords(self)
        obs['lap_progress'] = get_lap_progress(game, self.uni_index)
        obs['lap_number'] = get_lap_number(game, self.uni_index)
        lap_times, current = get_lap_timings(game, self.uni_index)
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
        prev_pos = track.get_start_position() + (carID * CAR_GAP)
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