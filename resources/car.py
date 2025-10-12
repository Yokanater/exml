import pybullet as p
import os
import math


class Car:
    def __init__(self, client):
        self.client = client
        f_name = os.path.join(os.path.dirname(__file__), 'car.urdf')
        self.car = p.loadURDF(fileName=f_name,
                              basePosition=[0, 0, 0.1],
                              physicsClientId=client)

        self.steering_joints = [0, 2]
        self.drive_joints = [1, 3, 4, 5]
        self.joint_speed = 0
        self.c_rolling = 0.2
        self.c_drag = 0.01
        self.c_throttle = 20

    def get_ids(self):
        return self.car, self.client

    def apply_action(self, action):
        if action is None:
            throttle = 0.0
            steering_angle = 0.0
        elif isinstance(action, int):
            if action == 0:
                throttle = 1.0
                steering_angle = 0.0
            elif action == 1:
                throttle = -1.0
                steering_angle = 0.0
            elif action == 2:
                throttle = 0.5
                steering_angle = -0.6
            elif action == 3:
                throttle = 0.5
                steering_angle = 0.6
            else:
                throttle = 0.0
                steering_angle = 0.0
        else:
            throttle, steering_angle = action

        throttle = min(max(throttle, -1), 1)
        steering_angle = max(min(steering_angle, 0.6), -0.6)

        p.setJointMotorControlArray(self.car, self.steering_joints,
                                    controlMode=p.POSITION_CONTROL,
                                    targetPositions=[steering_angle] * 2,
                                    physicsClientId=self.client)

        friction = -self.joint_speed * (self.joint_speed * self.c_drag + self.c_rolling)
        acceleration = self.c_throttle * throttle + friction
        self.joint_speed = self.joint_speed + 1/30 * acceleration

        p.setJointMotorControlArray(
            bodyUniqueId=self.car,
            jointIndices=self.drive_joints,
            controlMode=p.VELOCITY_CONTROL,
            targetVelocities=[self.joint_speed] * 4,
            forces=[1.2] * 4,
            physicsClientId=self.client)

    def get_observation(self):
        pos, ang = p.getBasePositionAndOrientation(self.car, self.client)
        ang = p.getEulerFromQuaternion(ang)
        ori = (math.cos(ang[2]), math.sin(ang[2]))
        pos = pos[:2]
        vel = p.getBaseVelocity(self.car, self.client)[0][0:2]

        observation = (pos + ori + vel)

        return observation









