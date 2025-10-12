import gymnasium as gym
import time
import envs
from render.render import GLRenderer


def run_manual():
    env = gym.make('Driving-v0', render_mode='rgb_array')
    ob, _ = env.reset()
    renderer = GLRenderer(width=400, height=400)

    keys = {'w': False, 's': False, 'a': False, 'd': False}

    @renderer.window.event
    def on_key_press(symbol, modifiers):
        if symbol == 119:
            keys['w'] = True
        elif symbol == 115:
            keys['s'] = True
        elif symbol == 97:
            keys['a'] = True
        elif symbol == 100:
            keys['d'] = True

    @renderer.window.event
    def on_key_release(symbol, modifiers):
        if symbol == 119:
            keys['w'] = False
        elif symbol == 115:
            keys['s'] = False
        elif symbol == 97:
            keys['a'] = False
        elif symbol == 100:
            keys['d'] = False

    while True:
        throttle = None
        steering = None
        if keys['w'] and not keys['s']:
            action = 0
        elif keys['s'] and not keys['w']:
            action = 1
        elif keys['a'] and not keys['d']:
            action = 2
        elif keys['d'] and not keys['a']:
            action = 3
        else:
            action = None

        ob, _, terminated, truncated, _ = env.step(action)
        done = terminated or truncated
        frame = env.render()
        if frame is not None:
            renderer.update_frame(frame)
            renderer.run_once()
        if done:
            ob, _ = env.reset()
        time.sleep(1/30)


if __name__ == '__main__':
    run_manual()
