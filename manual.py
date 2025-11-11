import pygame
from env.game import F1Game
from env.controls import forward, back, steer_right, steer_left
from env.braking import brake

def manual_control(car):
    keys = pygame.key.get_pressed()
    
    if keys[pygame.K_w]:
        forward(car)
    if keys[pygame.K_s]:
        back(car)
    if keys[pygame.K_a]:
        steer_right(car)
    if keys[pygame.K_d]:
        steer_left(car)
    if keys[pygame.K_SPACE]:
        brake(car)

if __name__ == "__main__":
    game = F1Game()
    game.run(manual_control)
