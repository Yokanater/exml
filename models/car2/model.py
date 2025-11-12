import pygame
from env.controls import forward, back, steer_right, steer_left, brake

def model(car):
    keys = pygame.key.get_pressed()
    
    if keys[pygame.K_UP]:
        forward(car)
    if keys[pygame.K_DOWN]:
        back(car)
    
    if keys[pygame.K_LEFT]:
        steer_left(car)
    if keys[pygame.K_RIGHT]:
        steer_right(car)
    
    if keys[pygame.K_BACKSPACE]:
        brake(car)

