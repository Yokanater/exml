extends CharacterBody2D

var wheelbase: float = 170.0
var max_steering_angle: float = deg_to_rad(120.0)
var steer_dirn: float = 0.0
var acc = Vector2.ZERO
var fric = -0.98
var drag = -0.001
var braking = -450
var maxrspeed = 250

var base_max_speed = 200
var accel_time = 0.0
var accel_duration = 8.0
var accel_target_kmph = 370.0
var base_speed_kmph = 50.0
var bezier_cp1y = 0.0
var bezier_cp2y = 1.0
var accel_amount = 800.0
var throttle: float = 0.0
var speed_print_timer: float = 0.0
var forward_block_timer: float = 0.0
var mass: float = 800.0
var collision_rebound: float = 0.75
var collision_layer_mask: int = 1

func _cubic_bezier_y(u):
	var t = clamp(u, 0.0, 1.0)
	var inv = 1.0 - t
	return 3.0 * inv * inv * t * bezier_cp1y + 3.0 * inv * t * t * bezier_cp2y + t * t * t

func _physics_process(delta: float) -> void:
	acc = Vector2.ZERO
	forward_block_timer = max(forward_block_timer - delta, 0.0)
	get_input()

	var accel_pressed = abs(throttle) > 0.0


	if accel_pressed:
		accel_time = min(accel_time + delta, accel_duration)
	else:
		accel_time = max(accel_time - delta, 0.0)

	var progress = accel_time / accel_duration
	var bez = _cubic_bezier_y(progress)

	var accel_multiplier = accel_target_kmph / base_speed_kmph
	var speed_multiplier = 1.0 + (accel_multiplier - 1.0) * bez

	if throttle != 0.0:
		acc += transform.x * accel_amount * bez * throttle

	app_fric()
	calculate_steering(delta)

	velocity += acc * delta

	speed_print_timer += delta
	if speed_print_timer >= 1.0:
		var signed_speed = velocity.dot(transform.x.normalized())
		print("velocity:", signed_speed)
		speed_print_timer -= 1.0

	var incoming_vel = velocity

	move_and_slide()

	var sc = get_slide_collision_count()
	for i in range(sc):
		var col = get_slide_collision(i)
		var collider = col.get_collider()
		if collider:
			if collider.has_method("get_collision_layer"):
				var layer = int(collider.get_collision_layer())
				if (layer & collision_layer_mask) == 0:
					continue
		var n = col.get_normal()
		var steer_factor = 0.0
		if max_steering_angle != 0.0:
			steer_factor = clamp(abs(steer_dirn) / max_steering_angle, 0.0, 1.0)
		var adjusted = n.rotated(steer_dirn)
		var blended_n = n.lerp(adjusted, steer_factor).normalized()
		var impact = -incoming_vel.dot(blended_n)
		if impact > 0.0:
			var recoil_speed = impact * collision_rebound
			velocity = Vector2.ZERO
			var recoil_dir = Vector2.ZERO
			if incoming_vel.length() > 0.001:
				recoil_dir = -incoming_vel.normalized()
			else:
				recoil_dir = blended_n
			var forward_dir = transform.x.normalized()
			if recoil_dir.dot(forward_dir) > 0.0:
				recoil_dir = -recoil_dir
			velocity = recoil_dir * recoil_speed
			forward_block_timer = 1.0
			break

func app_fric():
	if velocity.length() < 0.1 and throttle == 0.0:
		velocity = Vector2.ZERO
		return
	var fric_force = velocity * fric
	var drag_force = velocity * velocity.length() * drag
	acc += drag_force + fric_force

func get_input():
	var turn = 0
	if Input.is_action_pressed("ui_right"):
		turn += 1
	if Input.is_action_pressed("ui_left"):
		turn -= 1

	var speed = velocity.length()

	var normalized_speed = clamp(speed / 300.0, 0.0, 1.0)

	#var steering_sensitivity = 1.0 - pow(normalized_speed,1.05)
	var steering_sensitivity = 1.0 - pow(normalized_speed,1.05)
	var ss = max(steering_sensitivity, 0.05)

	#var dynamic_steering = max_steering_angle * steering_sensitivity
	var dynamic_steering = max_steering_angle * ss


	steer_dirn = turn * dynamic_steering

	throttle = 0.0
	if forward_block_timer <= 0.0:
		if Input.is_action_pressed("ui_up") or Input.is_key_pressed(KEY_UP) or Input.is_key_pressed(KEY_W):
			throttle += 1.0
	if Input.is_action_pressed("ui_down") or Input.is_key_pressed(KEY_DOWN) or Input.is_key_pressed(KEY_S):
		throttle -= 1.0
	if throttle <0: 
		steering_sensitivity *=1.2

func calculate_steering(delta: float) -> void:
	var rw = position - transform.x * (wheelbase / 2.0)
	var fw = position + transform.x * (wheelbase / 2.0)

	rw += velocity * delta
	fw += velocity.rotated(steer_dirn) * delta

	var new_dirn = (fw - rw).normalized()

	if velocity.length() > 5.0:
		var d = new_dirn.dot(velocity.normalized())
		if d > 0:
			velocity = new_dirn * velocity.length()
		elif d < 0:
			velocity = -new_dirn * min(velocity.length(), maxrspeed)
	else:
		velocity = new_dirn * velocity.length()

	rotation = new_dirn.angle()
