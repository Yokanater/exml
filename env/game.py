import pygame
import sys
from env.track import Track
from env.constants import CAR_GAP, CELL_SIZE
from car.car import Car
from env.camera import Camera
import os

class F1Game:
    def __init__(self):
        pygame.init()
        self._track = Track()
        self._screen_width = 1800
        self._screen_height = 1500
        self._screen = pygame.display.set_mode((self._screen_width, self._screen_height))
        pygame.display.set_caption("F1 Racing Environment")

        self._clock = pygame.time.Clock()
        self._fps = 60

        self._cars = []
        model_dirs = [d for d in os.listdir('models') if os.path.isdir(os.path.join('models', d))]
        for idx, model_dir in enumerate(model_dirs):
            start_x, start_y = self._track.get_start_position()
            car = Car(start_x + (idx*CAR_GAP), start_y, "assets/car.png", idx, start_x + (idx*CAR_GAP), start_y + (idx*CAR_GAP), self, self._track)
            self._cars.append(car)

        world_w = self._track.width * CELL_SIZE
        world_h = self._track.height * CELL_SIZE

        zoom_x = self._screen_width / world_w
        zoom_y = self._screen_height / world_h
        zoom = min(zoom_x, zoom_y)  
        
        self._camera = Camera(self._screen_width, self._screen_height, world_w, world_h, zoom=zoom)
        
        self._camera.offset_x = 0
        self._camera.offset_y = 0

        self._checkpoints_collected = {}
        self._laps_completed = {}
        self._lap_start_time = {}
        self._lap_times = {}
        self._next_checkpoint = {}
        for idx, model in enumerate(model_dirs):
            self._checkpoints_collected[idx] = set()
            self._laps_completed[idx] = 0
            self._lap_start_time[idx] = pygame.time.get_ticks()
            self._lap_times[idx] = []
            self._next_checkpoint[idx] = 1
        self._running = True
        
    def step(self):
        for idx, car in enumerate(self._cars):
            car.update(self._cars)
            
            car_x = car.get_observation()['x']
            car_y = car.get_observation()['y']
            checkpoint = self._track.check_checkpoint(car_x, car_y)
            
            if checkpoint is not None:
                if checkpoint == self._next_checkpoint[idx]:
                    self._checkpoints_collected[idx].add(checkpoint)
                    self._next_checkpoint[idx] = self._next_checkpoint[idx] + 1
                    if self._next_checkpoint[idx] > 9:
                        self._laps_completed[idx] += 1
                        now = pygame.time.get_ticks()
                        lap_time = (now - self._lap_start_time[idx]) / 1000.0
                        self._lap_times[idx].append(lap_time)
                        self._lap_start_time[idx] = now
                        self._checkpoints_collected[idx] = set()
                        self._next_checkpoint[idx] = 1
    
    def render(self):
        self._screen.fill((0, 0, 0))

        self._track.render(self._screen, self._camera)
        
        for idx, car in enumerate(self._cars):
            car.render(self._screen, self._camera)
        
        if self._cars:
            font = pygame.font.Font(None, 24)
            for idx, car in enumerate(self._cars):
                laps = self._laps_completed.get(idx, 0)
                checkpoints = len(self._checkpoints_collected.get(idx, set()))
                text = font.render(f"Car {idx+1}: Lap {laps+1}, CP {checkpoints}/9", True, (255, 255, 255))
                self._screen.blit(text, (10, 10 + idx * 25))
        
        pygame.display.flip()
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
                pygame.quit()
                sys.exit()
    
    def run(self, control_funcs=None):
        while self._running:
            self.handle_events()
            
            if control_funcs:
                if len(control_funcs) != len(self._cars):
                    print("Mismatch: control_funcs=" + str(len(control_funcs)) + ", cars=" + str(len(self._cars)))
                    self._running = False
                else:
                    for idx, car in enumerate(self._cars):
                        control_funcs[idx](car)
            
            self.step()
            self.render()
            self._clock.tick(self._fps)
        
        pygame.quit()