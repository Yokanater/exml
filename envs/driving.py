import gymnasium as gym
import numpy as np
import os
import math
import pybullet as p
from resources.car import Car
from resources.plane import Plane
from resources.goal import Goal
import matplotlib.pyplot as plt


class DrivingEnv(gym.Env):
	metadata = {'render.modes': ['human', 'rgb_array']}

	def __init__(self, render_mode=None):
		self.action_space = gym.spaces.Discrete(4)
		self.render_mode = render_mode
		self.observation_space = gym.spaces.box.Box(
			low=np.array([-10, -10, -1, -1, -5, -5, -10, -10], dtype=np.float32),
			high=np.array([10, 10, 1, 1, 5, 5, 10, 10], dtype=np.float32))
		self.np_random, _ = gym.utils.seeding.np_random()

		self.client = p.connect(p.DIRECT)
		p.setTimeStep(1/30, self.client)

		self.car = None
		self.goal = None
		self.done = False
		self.prev_dist_to_goal = None
		self.rendered_img = None
		self.reset()

	def step(self, action):
		self.car.apply_action(action)
		p.stepSimulation()
		car_ob = self.car.get_observation()

		dist_to_goal = math.sqrt(((car_ob[0] - self.goal[0]) ** 2 +
								  (car_ob[1] - self.goal[1]) ** 2))
		reward = max(self.prev_dist_to_goal - dist_to_goal, 0)
		self.prev_dist_to_goal = dist_to_goal

		if (car_ob[0] >= 10 or car_ob[0] <= -10 or
				car_ob[1] >= 10 or car_ob[1] <= -10):
			self.done = True
		elif dist_to_goal < 1:
			self.done = True
			reward = 50

		ob = np.array(car_ob + self.goal, dtype=np.float32)
		terminated = self.done
		truncated = False
		return ob, reward, terminated, truncated, {}

	def seed(self, seed=None):
		self.np_random, seed = gym.utils.seeding.np_random(seed)
		return [seed]

	def reset(self, *, seed=None, options=None):
		p.resetSimulation(self.client)
		p.setGravity(0, 0, -10)
		Plane(self.client)
		self.car = Car(self.client)

		x = (self.np_random.uniform(5, 9) if self.np_random.integers(2) else
			self.np_random.uniform(-9, -5))
		y = (self.np_random.uniform(5, 9) if self.np_random.integers(2) else
			self.np_random.uniform(-9, -5))
		self.goal = (x, y)
		self.done = False

		Goal(self.client, self.goal)

		car_ob = self.car.get_observation()

		self.prev_dist_to_goal = math.sqrt(((car_ob[0] - self.goal[0]) ** 2 +
						   (car_ob[1] - self.goal[1]) ** 2))
		return np.array(car_ob + self.goal, dtype=np.float32), {}

	def render(self):
		mode = self.render_mode or 'human'
		car_id, client_id = self.car.get_ids()
		proj_matrix = p.computeProjectionMatrixFOV(fov=80, aspect=1,
					   nearVal=0.01, farVal=100)
		pos, ori = [list(item) for item in
				p.getBasePositionAndOrientation(car_id, client_id)]
		pov = int(os.environ.get('POV', '0')) if 'os' in globals() else 0
		if pov == 0:
			camera_height = 15
			camera_pos = [pos[0], pos[1], pos[2] + camera_height]
			target_pos = [pos[0], pos[1], 0]
			up_vec = [0, 1, 0]
			view_matrix = p.computeViewMatrix(camera_pos, target_pos, up_vec)
		else:
			rot_mat = np.array(p.getMatrixFromQuaternion(ori)).reshape(3, 3)
			camera_vec = np.matmul(rot_mat, [1, 0, 0])
			up_vec = np.matmul(rot_mat, np.array([0, 0, 1]))
			view_matrix = p.computeViewMatrix(pos, pos + camera_vec, up_vec)

		width, height = 400, 400
		img = p.getCameraImage(width, height, view_matrix, proj_matrix)
		frame = np.reshape(img[2], (height, width, 4)).astype(np.uint8)
		if mode == 'rgb_array':
			return frame[:, :, :3]
		if self.rendered_img is None:
			self.rendered_img = plt.imshow(np.zeros((height, width, 4)))
		self.rendered_img.set_data(frame)
		plt.draw()
		plt.pause(.00001)

	def close(self):
		p.disconnect(self.client)

