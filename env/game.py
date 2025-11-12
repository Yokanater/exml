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
        self.track = Track()
        self.screen_width = 1800
        self.screen_height = 1500
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("F1 Racing Environment")

        self.clock = pygame.time.Clock()
        self.fps = 60

        self.cars = []
        model_dirs = [d for d in os.listdir('models') if os.path.isdir(os.path.join('models', d))]
        for idx, model_dir in enumerate(model_dirs):
            start_x, start_y = self.track.get_start_position()
            car = Car(start_x + (idx*CAR_GAP), start_y, "assets/car.png", idx, start_x + (idx*CAR_GAP), start_y + (idx*CAR_GAP))
            self.cars.append(car)

        world_w = self.track.width * CELL_SIZE
        world_h = self.track.height * CELL_SIZE

        zoom_x = self.screen_width / world_w
        zoom_y = self.screen_height / world_h
        zoom = min(zoom_x, zoom_y)  
        
        self.camera = Camera(self.screen_width, self.screen_height, world_w, world_h, zoom=zoom)
        
        self.camera.offset_x = 0
        self.camera.offset_y = 0

        self.checkpoints_collected = {}
        self.laps_completed = {}
        self.lap_start_time = {}
        self.lap_times = {}
        self.next_checkpoint = {}
        for idx, model in enumerate(model_dirs):
            self.checkpoints_collected[idx] = set()
            self.laps_completed[idx] = 0
            self.lap_start_time[idx] = pygame.time.get_ticks()
            self.lap_times[idx] = []
            self.next_checkpoint[idx] = 1
        self.running = True
        
    def step(self):
        for idx, car in enumerate(self.cars):
            car.update(self.track, self.cars)
            
            car_x, car_y = car.get_position()
            checkpoint = self.track.check_checkpoint(car_x, car_y)
            
            if checkpoint is not None:
                if checkpoint == self.next_checkpoint[idx]:
                    self.checkpoints_collected[idx].add(checkpoint)
                    self.next_checkpoint[idx] = self.next_checkpoint[idx] + 1
                    if self.next_checkpoint[idx] > 9:
                        self.laps_completed[idx] += 1
                        now = pygame.time.get_ticks()
                        lap_time = (now - self.lap_start_time[idx]) / 1000.0
                        self.lap_times[idx].append(lap_time)
                        self.lap_start_time[idx] = now
                        self.checkpoints_collected[idx] = set()
                        self.next_checkpoint[idx] = 1
    
    def render(self):
        self.screen.fill((0, 0, 0))

        self.track.render(self.screen, self.camera)
        
        for idx, car in enumerate(self.cars):
            car.render(self.screen, self.camera)
        
        # lap inf
        if self.cars:
            font = pygame.font.Font(None, 24)
            for idx, car in enumerate(self.cars):
                laps = self.laps_completed.get(idx, 0)
                checkpoints = len(self.checkpoints_collected.get(idx, set()))
                text = font.render(f"Car {idx+1}: Lap {laps+1}, CP {checkpoints}/9", True, (255, 255, 255))
                self.screen.blit(text, (10, 10 + idx * 25))
        
        pygame.display.flip()
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                pygame.quit()
                sys.exit()
    
    def run(self, control_funcs=None):
        while self.running:
            self.handle_events()
            
            if control_funcs:
                if len(control_funcs) != len(self.cars):
                    print("Mismatch: control_funcs=" + str(len(control_funcs)) + ", cars=" + str(len(self.cars)))
                    self.running = False
                else:
                    for idx, car in enumerate(self.cars):
                        control_funcs[idx](car)
            
            self.step()
            self.render()
            self.clock.tick(self.fps)
        
        pygame.quit()
