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

        self.boost_request = False
        self.boost_active = False
        self.boost_ramp = 0.0
        self.boost_ramp_rate = 3.0 
        self.boost_decay_rate = 2.0
        self.boost_multiplier = 1.8

        self.recent_accel = 0.0
        self.recent_accel_alpha = 0.2

        self.boost_cooldown = 10.0
        self.boost_cooldown_timer = 0.0

        self.c_brake = 40.0
        self.brake_ramp = 0.0
        self.brake_ramp_rate = 0.8
        self.brake_decay_rate = 6.0

    def get_ids(self):
        return self.car, self.client

    def apply_action(self, action):
        boost = False
        brake = 0.0
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
        elif isinstance(action, tuple) or isinstance(action, list):
            if len(action) == 2:
                throttle, steering_angle = action
            else:
                throttle, steering_angle, boost = action[0], action[1], action[2]
                if len(action) > 3:
                    brake = action[3]
        elif isinstance(action, dict):
            throttle = action.get('throttle', 0.0)
            steering_angle = action.get('steering', 0.0)
            boost = action.get('boost', False)
            brake = action.get('brake', 0.0)
        else:
            throttle, steering_angle = action

        throttle = min(max(throttle, -1), 1)
        steering_angle = max(min(steering_angle, 0.6), -0.6)
        brake = min(max(brake, 0.0), 1.0)

        p.setJointMotorControlArray(self.car, self.steering_joints,
                                    controlMode=p.POSITION_CONTROL,
                                    targetPositions=[steering_angle] * 2,
                                    physicsClientId=self.client)

        self.recent_accel = (1 - self.recent_accel_alpha) * self.recent_accel + self.recent_accel_alpha * throttle

        can_boost = throttle > 0.2 and 0.3 < abs(self.recent_accel) < 0.9
        self.boost_request = False
        if self.boost_cooldown_timer <= 0.0 and bool(boost) and can_boost:
            self.boost_request = True

        self.boost_cooldown_timer = max(0.0, self.boost_cooldown_timer - (1/30))

        if self.boost_request:
            self.boost_ramp = min(1.0, self.boost_ramp + self.boost_ramp_rate * (1/30))
        else:
            self.boost_ramp = max(0.0, self.boost_ramp - self.boost_decay_rate * (1/30))

        if brake > 0.0:
            self.brake_ramp = min(1.0, self.brake_ramp + self.brake_ramp_rate * (1/30))
        else:
            self.brake_ramp = max(0.0, self.brake_ramp - self.brake_decay_rate * (1/30))

        prev_boost_active = self.boost_active
        self.boost_active = self.boost_ramp > 0.01

        if prev_boost_active and (not self.boost_active) and self.boost_ramp < 0.2:
            self.boost_cooldown_timer = self.boost_cooldown

        effective_throttle = throttle * (1.0 + (self.boost_multiplier - 1.0) * self.boost_ramp)

        friction = -self.joint_speed * (self.joint_speed * self.c_drag + self.c_rolling)
        acceleration = self.c_throttle * effective_throttle + friction
        self.joint_speed = self.joint_speed + 1/30 * acceleration

        if self.brake_ramp > 0.01:
            pos, ori = p.getBasePositionAndOrientation(self.car, self.client)
            rot = p.getMatrixFromQuaternion(ori)
            forward = (rot[0], rot[3], rot[6])
            lin_vel = p.getBaseVelocity(self.car, self.client)[0]
            forward_speed = lin_vel[0] * forward[0] + lin_vel[1] * forward[1] + lin_vel[2] * forward[2]
            brake_delta = self.c_brake * self.brake_ramp * (1/30)
            if forward_speed > 0:
                new_forward_speed = max(0.0, forward_speed - brake_delta)
            elif forward_speed < 0:
                new_forward_speed = min(0.0, forward_speed + brake_delta)
            else:
                new_forward_speed = 0.0
            dv = new_forward_speed - forward_speed
            new_lin_vel = [lin_vel[0] + dv * forward[0], lin_vel[1] + dv * forward[1], lin_vel[2] + dv * forward[2]]
            p.resetBaseVelocity(self.car, linearVelocity=new_lin_vel, physicsClientId=self.client)
            self.joint_speed = new_forward_speed

        max_force = 1.2 * (1.0 + 0.5 * self.boost_ramp)

        if self.brake_ramp > 0.01:
            p.setJointMotorControlArray(
                bodyUniqueId=self.car,
                jointIndices=self.drive_joints,
                controlMode=p.VELOCITY_CONTROL,
                targetVelocities=[self.joint_speed] * 4,
                forces=[0.0] * 4,
                physicsClientId=self.client)
        else:
            p.setJointMotorControlArray(
                bodyUniqueId=self.car,
                jointIndices=self.drive_joints,
                controlMode=p.VELOCITY_CONTROL,
                targetVelocities=[self.joint_speed] * 4,
                forces=[max_force] * 4,
                physicsClientId=self.client)

    def get_observation(self):
        pos, ang = p.getBasePositionAndOrientation(self.car, self.client)
        ang = p.getEulerFromQuaternion(ang)
        ori = (math.cos(ang[2]), math.sin(ang[2]))
        pos = pos[:2]
        vel = p.getBaseVelocity(self.car, self.client)[0][0:2]

        observation = (pos + ori + vel)

        return observation









