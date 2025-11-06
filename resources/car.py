import pybullet as p
import os
import math


class Car:
    def __init__(self, client, base_position=None, scale=0.2):
        self.client = client
        self.scale = float(scale)
        f_name = os.path.join(os.path.dirname(__file__), 'car.urdf')
        bp = base_position if base_position is not None else [0, 0, 0.1 * self.scale]
        self.car = p.loadURDF(fileName=f_name,
                              basePosition=bp,
                              globalScaling=self.scale,
                              physicsClientId=client)
        quat = p.getQuaternionFromEuler([0, 0, 0])
        p.resetBasePositionAndOrientation(self.car, bp, quat, physicsClientId=self.client)
        p.resetBaseVelocity(self.car, linearVelocity=[0, 0, 0], angularVelocity=[0, 0, 0], physicsClientId=self.client)

        self.steering_joints = [0, 2]
        self.drive_joints = [1, 3, 4, 5]
        self.joint_speed = 0
        self.c_rolling = 0.2
        self.c_drag = 0.01
        self.c_throttle = 80

        self.max_drive_force = 400.0

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

        self.c_brake = 30.0
        self.brake_ramp = 0.0
        self.brake_ramp_rate = 0.8
        self.brake_decay_rate = 6.0
        self.collision_stun = 0.0
        self.c_downforce = 10.0
        self.c_angular_damping = 1.0
        self.c_kanav_powder = 10.0
        self.default_linear_damping = 0.6
        self.default_angular_damping = 12.0
        self.c_stabilize_angle = 120.0
        self.c_stabilize_angvel = 12.0
        self.c_stabilize_max_torque = 200.0
        p.changeDynamics(self.car, -1, linearDamping=self.default_linear_damping, angularDamping=self.default_angular_damping, physicsClientId=self.client)
        for link_idx in (self.steering_joints + self.drive_joints):
            p.changeDynamics(self.car, link_idx, lateralFriction=1.0, spinningFriction=0.1, rollingFriction=0.01, angularDamping=self.default_angular_damping * 0.5, physicsClientId=self.client)

    def get_ids(self):
        return self.car, self.client

    def handle_collisions(self):
        contacts = p.getContactPoints(bodyA=self.car, physicsClientId=self.client)
        total_weight = 0.0
        weighted_normal = [0.0, 0.0, 0.0]
        max_impact = 0.0
        vA = p.getBaseVelocity(self.car, self.client)[0]
        for cp in contacts:
            other = cp[2]
            if other >= 0:
                dyn = p.getDynamicsInfo(other, -1, physicsClientId=self.client)
                if dyn is not None and len(dyn) > 0 and dyn[0] == 0.0:
                    continue
            normal_on_b = cp[7]
            if abs(normal_on_b[2]) > 0.5:
                continue
            if other >= 0:
                vB = p.getBaseVelocity(other, self.client)[0]
            else:
                vB = (0.0, 0.0, 0.0)
            vrel = (vA[0] - vB[0], vA[1] - vB[1], vA[2] - vB[2])
            normal_a = (-normal_on_b[0], -normal_on_b[1], -normal_on_b[2])
            impact_speed = max(0.0, vrel[0] * normal_a[0] + vrel[1] * normal_a[1] + vrel[2] * normal_a[2])
            if impact_speed <= 0.05:
                continue
            weighted_normal[0] += normal_on_b[0] * impact_speed
            weighted_normal[1] += normal_on_b[1] * impact_speed
            weighted_normal[2] += normal_on_b[2] * impact_speed
            total_weight += impact_speed
            if impact_speed > max_impact:
                max_impact = impact_speed
        if total_weight == 0.0:
            return
        avg_normal = (weighted_normal[0] / total_weight, weighted_normal[1] / total_weight, weighted_normal[2] / total_weight)
        impact_val = max_impact
        rebound = 5.0
        pos, ori = p.getBasePositionAndOrientation(self.car, self.client)
        rot = p.getMatrixFromQuaternion(ori)
        forward = (rot[0], rot[3], rot[6])
        lin_vel = vA
        forward_speed = lin_vel[0] * forward[0] + lin_vel[1] * forward[1] + lin_vel[2] * forward[2]
        vel_no_forward = (lin_vel[0] - forward[0] * forward_speed,
                        lin_vel[1] - forward[1] * forward_speed,
                        lin_vel[2] - forward[2] * forward_speed)
        bounce = (avg_normal[0] * impact_val * rebound,
                avg_normal[1] * impact_val * rebound,
                avg_normal[2] * impact_val * rebound)
        new_vel = (vel_no_forward[0] + bounce[0], vel_no_forward[1] + bounce[1], vel_no_forward[2] + bounce[2])
        p.resetBaseVelocity(self.car, linearVelocity=new_vel, physicsClientId=self.client)
        self.joint_speed = 0.0
        p.setJointMotorControlArray(bodyUniqueId=self.car,
                                    jointIndices=self.drive_joints,
                                    controlMode=p.VELOCITY_CONTROL,
                                    targetVelocities=[0.0] * len(self.drive_joints),
                                    forces=[0.0] * len(self.drive_joints),
                                    physicsClientId=self.client)
        self.collision_stun = max(self.collision_stun, 1.0)

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

        self.collision_stun = max(0.0, self.collision_stun - (1/30))
        if self.collision_stun > 0.0:
            throttle = 0.0
            steering_angle = 0.0
            boost = False
            brake = 0.0

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

        max_force = max(10.0, self.c_throttle * (1.0 + 0.5 * self.boost_ramp))
        max_force = min(max_force, self.max_drive_force)

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
            self.joint_speed = new_forward_speed
            extra_damping = min(2.0, self.brake_ramp * 2.0)
            p.changeDynamics(self.car, -1, linearDamping=self.default_linear_damping + extra_damping, angularDamping=self.default_angular_damping + extra_damping * 0.5, physicsClientId=self.client)
        else:
            p.changeDynamics(self.car, -1, linearDamping=self.default_linear_damping, angularDamping=self.default_angular_damping, physicsClientId=self.client)


        if self.collision_stun > 0.0:
            max_force = 0.0

        if self.brake_ramp > 0.01:
            brake_motor_force = max_force * (1.0 + 2.0 * self.brake_ramp)
            brake_motor_force = max(0.0, min(brake_motor_force, self.max_drive_force * 4.0))
            p.setJointMotorControlArray(
                bodyUniqueId=self.car,
                jointIndices=self.drive_joints,
                controlMode=p.VELOCITY_CONTROL,
                targetVelocities=[0.0] * 4,
                forces=[brake_motor_force] * 4,
                physicsClientId=self.client)
        else:
            p.setJointMotorControlArray(
                bodyUniqueId=self.car,
                jointIndices=self.drive_joints,
                controlMode=p.VELOCITY_CONTROL,
                targetVelocities=[self.joint_speed] * 4,
                forces=[max_force] * 4,
                physicsClientId=self.client)

        pos, ori = p.getBasePositionAndOrientation(self.car, self.client)
        rot = p.getMatrixFromQuaternion(ori)
        forward = (rot[0], rot[3], rot[6])
        lin_vel, ang_vel = p.getBaseVelocity(self.car, self.client)
        forward_speed = lin_vel[0] * forward[0] + lin_vel[1] * forward[1] + lin_vel[2] * forward[2]

        speed_for_down = max(0.0, forward_speed)
        downforce = -self.c_downforce * speed_for_down * abs(speed_for_down)
        p.applyExternalForce(self.car, -1, [0.0, 0.0, downforce], pos, p.WORLD_FRAME, physicsClientId=self.client)
        euler = p.getEulerFromQuaternion(ori)
        roll = 0.0
        pitch = 0.0
        yaw = euler[2]
        if yaw < -math.pi:
            yaw += 2.0 * math.pi
        elif yaw > math.pi:
            yaw -= 2.0 * math.pi
        max_yaw_rate = 2.0
        ang_z = ang_vel[2]
        if ang_z < -max_yaw_rate:
            ang_z = -max_yaw_rate
        elif ang_z > max_yaw_rate:
            ang_z = max_yaw_rate
        ang_vel = (ang_vel[0], ang_vel[1], ang_z)
        for name, jlist in (("steer", self.steering_joints), ("drive", self.drive_joints)):
            for i, idx in enumerate(jlist):
                js = p.getJointState(self.car, idx, physicsClientId=self.client)
                if js is None:
                    continue
                jpos = js[0]
                jvel = js[1]
                jtorque = js[3] if len(js) > 3 else 0.0
                print("joint {}_{} idx {}: pos: {:.3f} rad, vel: {:.3f} rad/s, torque: {:.3f}".format(name, i, idx, jpos, jvel, jtorque))
        max_angle = max(abs(roll), abs(pitch))
        if max_angle > math.radians(50):
            new_ang = (ang_vel[0] * 0.05, ang_vel[1] * 0.05, ang_vel[2] * 0.2)
            p.resetBaseVelocity(self.car, linearVelocity=lin_vel, angularVelocity=new_ang, physicsClientId=self.client)
            p.changeDynamics(self.car, -1, angularDamping=self.default_angular_damping + 50.0, physicsClientId=self.client)
        else:
            p.changeDynamics(self.car, -1, angularDamping=self.default_angular_damping, physicsClientId=self.client)
        local_t_x = - (self.c_stabilize_angle * roll + self.c_stabilize_angvel * ang_vel[0])
        local_t_y = - (self.c_stabilize_angle * pitch + self.c_stabilize_angvel * ang_vel[1])
        local_t_z = - (0.5 * self.c_stabilize_angle * yaw + 0.5 * self.c_stabilize_angvel * ang_vel[2])
        max_z_torque = self.c_stabilize_max_torque * 0.5
        if abs(local_t_z) > max_z_torque and max_z_torque > 0.0:
            local_t_z = max_z_torque * (local_t_z / abs(local_t_z))
        col0 = (rot[0], rot[3], rot[6])
        col1 = (rot[1], rot[4], rot[7])
        col2 = (rot[2], rot[5], rot[8])
        torque_world = (local_t_x * col0[0] + local_t_y * col1[0] + local_t_z * col2[0],
                local_t_x * col0[1] + local_t_y * col1[1] + local_t_z * col2[1],
                local_t_x * col0[2] + local_t_y * col1[2] + local_t_z * col2[2])
        torque_norm = math.sqrt(torque_world[0] * torque_world[0] + torque_world[1] * torque_world[1] + torque_world[2] * torque_world[2])
        if torque_norm > self.c_stabilize_max_torque and torque_norm > 0.0:
            scale = self.c_stabilize_max_torque / torque_norm
            torque_world = (torque_world[0] * scale, torque_world[1] * scale, torque_world[2] * scale)
        p.applyExternalTorque(self.car, -1, torque_world, p.WORLD_FRAME, physicsClientId=self.client)

    def get_observation(self):
        pos, ang = p.getBasePositionAndOrientation(self.car, self.client)
        ang = p.getEulerFromQuaternion(ang)
        ori = (math.cos(ang[2]), math.sin(ang[2]))
        pos = pos[:2]
        vel = p.getBaseVelocity(self.car, self.client)[0][0:2]

        observation = (pos + ori + vel)

        return observation









