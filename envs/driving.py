import gymnasium as gym
import numpy as np
import os
import math
import pybullet as p
from resources.car import Car
from resources.plane import Plane
from resources.track import Track

import matplotlib.pyplot as plt


class DrivingEnv(gym.Env):
	metadata = {'render_modes': ['human', 'rgb_array'], 'render_fps': 30}


	def __init__(self, render_mode=None):
		self.action_space = gym.spaces.Dict({
			'act': gym.spaces.Discrete(4),
			'boost': gym.spaces.Discrete(2),
			'brake': gym.spaces.Discrete(2)
		})
		self.render_mode = render_mode
		self.world_bounds = ((-10.0, 10.0), (-10.0, 10.0))
		xmin, xmax = self.world_bounds[0]
		ymin, ymax = self.world_bounds[1]
		self.observation_space = gym.spaces.box.Box(
			low=np.array([xmin, ymin, -1, -1, -5, -5, xmin, ymin], dtype=np.float32),
			high=np.array([xmax, ymax, 1, 1, 5, 5, xmax, ymax], dtype=np.float32))
		self.np_random, _ = gym.utils.seeding.np_random()

		self.client = p.connect(p.DIRECT)
		p.setTimeStep(1/30, self.client)
		self.physics_substeps = 4

		self.car = None
		self.goal = None
		self.done = False
		self.prev_dist_to_goal = None
		self.rendered_img = None
		self.reset()

	def step(self, action):
		if isinstance(action, dict) and 'act' in action:
			act = action.get('act')
			boost = bool(action.get('boost', 0))
			brake = action.get('brake', 0)
			if act is None:
				self.car.apply_action({'throttle': 0.0, 'steering': 0.0, 'boost': boost, 'brake': brake})
			else:
				self._apply_act_with_boost(act, boost, brake)
		else:
			self.car.apply_action(action)
		for _ in range(getattr(self, 'physics_substeps', 1)):
			p.stepSimulation()
		self.car.handle_collisions()
		car_ob = self.car.get_observation()
		car_pos = (car_ob[0], car_ob[1])
		cp_result = None
		if hasattr(self, 'track') and self.track is not None:
			cp_result = self.track.check_and_advance(car_pos)



		reward = 0
		if cp_result == 'checkpoint':
			reward = 1
		elif cp_result == 'lap':
			reward = 100
			self.done = True

		xmin, xmax = self.world_bounds[0]
		ymin, ymax = self.world_bounds[1]
		if (car_ob[0] > xmax or car_ob[0] < xmin or car_ob[1] > ymax or car_ob[1] < ymin):
			self.done = True

		if hasattr(self, 'track') and self.track is not None:
			lap_coord = self.track.lap_start
		else:
			lap_coord = (0.0, 0.0)
		ob = np.array(car_ob + lap_coord, dtype=np.float32)
		terminated = self.done
		truncated = False
		return ob, reward, terminated, truncated, {}

	def _apply_act_with_boost(self, act, boost, brake):
		if act == 0:
			throttle = 1.0
			steering_angle = 0.0
		elif act == 1:
			throttle = -1.0
			steering_angle = 0.0
		elif act == 2:
			throttle = 0.5
			steering_angle = -0.6
		elif act == 3:
			throttle = 0.5
			steering_angle = 0.6
		else:
			throttle = 0.0
			steering_angle = 0.0
		self.car.apply_action({'throttle': throttle, 'steering': steering_angle, 'boost': bool(boost), 'brake': brake})

	def seed(self, seed=None):
		self.np_random, seed = gym.utils.seeding.np_random(seed)
		return [seed]

	def reset(self, *, seed=None, options=None):
		p.resetSimulation(self.client)
		p.setGravity(0, 0, -10, physicsClientId=self.client)
		plane = Plane(self.client)
		try:
			(xmin, xmax), (ymin, ymax) = plane.get_bounds()
			self.world_bounds = ((float(xmin), float(xmax)), (float(ymin), float(ymax)))
			self.observation_space = gym.spaces.box.Box(
				low=np.array([xmin, ymin, -1, -1, -5, -5, xmin, ymin], dtype=np.float32),
				high=np.array([xmax, ymax, 1, 1, 5, 5, xmax, ymax], dtype=np.float32))
		except Exception:
			pass



		lap_start = (0, 0)
		checkpoints = [(3, 0), (3, 3), (0, 3), (-3, 3), (-3, 0), (-3, -3), (0, -3), (3, -3)]
		self.track = Track(self.client, lap_start, checkpoints)
		self.done = False

		track_spawn = None
		try:
			track_spawn = self.track.get_spawn()
		except Exception:
			track_spawn = None

		if track_spawn is not None:
			spawn = (float(track_spawn[0]), float(track_spawn[1]))
		else:
			min_dist = 1.5
			candidates = [(lap_start[0]-2, lap_start[1]), (lap_start[0]+2, lap_start[1]), (lap_start[0], lap_start[1]-2), (lap_start[0], lap_start[1]+2), (lap_start[0]+4, lap_start[1]), (lap_start[0]-4, lap_start[1])]
			spawn = None
			for c in candidates:
				ok = True
				for cp in checkpoints + [lap_start]:
					if math.hypot(c[0]-cp[0], c[1]-cp[1]) < min_dist:
						ok = False
						break
				if ok:
					spawn = c
					break
			if spawn is None:
				spawn = (lap_start[0] + 5, lap_start[1])

		self.car = Car(self.client, base_position=[spawn[0], spawn[1], 0.55])

		car_ob = self.car.get_observation()

		self.prev_dist_to_goal = None
		self.track.reset()
		return np.array(car_ob + (0.0, 0.0), dtype=np.float32), {}

	def render(self):
		mode = self.render_mode or 'human'
		car_id, client_id = self.car.get_ids()
		proj_matrix = p.computeProjectionMatrixFOV(fov=45, aspect=1,
				   nearVal=0.01, farVal=100)
		pos, ori = [list(item) for item in
				p.getBasePositionAndOrientation(car_id, client_id)]
		pov = int(os.environ.get('POV', '0')) if 'os' in globals() else 0
		if pov == 0:
			camera_height = 5
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

