import pygame
import sys
from env.track import Track, CELL_SIZE
from car.car import Car
from env.camera import Camera

class F1Game:
    def __init__(self):
        pygame.init()
        self.track = Track()
        self.screen_width = 800
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("F1 Racing Environment")

        self.clock = pygame.time.Clock()
        self.fps = 60

        start_x, start_y = self.track.get_start_position()
        self.car = Car(start_x, start_y, "assets/car.png")
        world_w = self.track.width * CELL_SIZE
        world_h = self.track.height * CELL_SIZE
        self.camera = Camera(self.screen_width, self.screen_height, world_w, world_h, zoom=4.0)

        self.checkpoints_collected = set()
        self.laps_completed = 0
        self.lap_start_time = pygame.time.get_ticks()
        self.lap_times = []
        self.next_checkpoint = 1
        self.running = True
        
    def reset(self):
        start_x, start_y = self.track.get_start_position()
        self.car.reset(start_x, start_y)
        self.checkpoints_collected = set()
        self.laps_completed = 0
        
    def step(self):
        self.car.update(self.track)
        
        car_x, car_y = self.car.get_position()
        checkpoint = self.track.check_checkpoint(car_x, car_y)
        
        if checkpoint is not None:
            if checkpoint == getattr(self, 'next_checkpoint', 1):
                self.checkpoints_collected.add(checkpoint)
                self.next_checkpoint = self.next_checkpoint + 1
                if self.next_checkpoint > 9:
                    self.laps_completed += 1
                    import pygame
                    now = pygame.time.get_ticks()
                    lap_time = (now - getattr(self, 'lap_start_time', now)) / 1000.0
                    self.lap_times.append(lap_time)
                    self.lap_start_time = now
                    self.checkpoints_collected = set()
                    self.next_checkpoint = 1
        
        reward = 0
        done = False

        return reward, done
    
    def render(self):
        self.screen.fill((0, 0, 0))
        self.camera.update(self.car)
        self.track.render(self.screen, camera=self.camera)
        self.car.render(self.screen, camera=self.camera)
        
        font = pygame.font.Font(None, 36)
        text = font.render(f"Checkpoints: {len(self.checkpoints_collected)}/9  Laps: {self.laps_completed}", True, (255, 255, 255))
        self.screen.blit(text, (10, 10))
        
        pygame.display.flip()
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                pygame.quit()
                sys.exit()
        
    def run(self, control_func=None):
        while self.running:
            self.handle_events()
            
            if control_func:
                control_func(self.car)
            
            reward, done = self.step()
            
            if done:
                self.reset()
            
            self.render()
            self.clock.tick(self.fps)
        
        pygame.quit()
