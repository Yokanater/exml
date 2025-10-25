import gymnasium as gym
import time
import envs
from render.render import GLRenderer


def run_manual():
    env = gym.make('Driving-v0', render_mode='rgb_array')
    ob, _ = env.reset()
    renderer = GLRenderer(width=400, height=400)

    keys = {'w': False, 's': False, 'a': False, 'd': False}
    shift = {'down': False}
    brake = {'down': False}
    prev_boost = False
    prev_brake = False

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
        elif symbol in (65505, 65506):
            shift['down'] = True
        elif symbol == 32:
            brake['down'] = True

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
        elif symbol in (65505, 65506):
            shift['down'] = False
        elif symbol == 32:
            brake['down'] = False

    while True:
        throttle = 0.0
        if keys['w'] and not keys['s']:
            throttle = 1.0
        elif keys['s'] and not keys['w']:
            throttle = -1.0

        steering = 0.0
        if keys['a'] and not keys['d']:
            steering = -0.6
        elif keys['d'] and not keys['a']:
            steering = 0.6

        is_boost = 1 if shift['down'] else 0
        is_brake = 1 if brake['down'] else 0
        step_action = {'throttle': throttle, 'steering': steering, 'boost': is_boost, 'brake': is_brake}
        if is_boost and not prev_boost:
            print('boost started')
        if is_brake and not prev_brake:
            print('brake started')
        prev_boost = bool(is_boost)
        prev_brake = bool(is_brake)

        ob, _, terminated, truncated, _ = env.step(step_action)
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
