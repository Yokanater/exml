import gymnasium as gym
import time
import envs
from render.render import GLRenderer


def main():
    env = gym.make('Driving-v0')
    ob, _ = env.reset()
    renderer = GLRenderer(width=400, height=400)
    while True:
        action = env.action_space.sample()
        ob, _, terminated, truncated, _ = env.step(action)
        done = terminated or truncated
        frame = env.render(mode='rgb_array')
        if frame is not None:
            renderer.update_frame(frame)
            renderer.run_once()
        if done:
            ob, _ = env.reset()
            time.sleep(1/30)


if __name__ == '__main__':
    main()
