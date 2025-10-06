extends CharacterBody2D

var wheelbase: float = 170.0
var max_steering_angle: float = deg_to_rad(120.0)
var steer_dirn: float = 0.0
var acc: Vector2 = Vector2.ZERO
var fric: float = -0.98
var drag: float = -0.001
var braking: float = -450
var maxrspeed: float = 250

var base_max_speed = 200
var accel_time: float = 0.0
var accel_duration: float = 8.0
var accel_target_kmph: float = 370.0
var base_speed_kmph: float = 50.0
var bezier_cp1y: float = 0.0
var bezier_cp2y: float = 1.0
var accel_amount: float = 800.0
var throttle: float = 0.0
var speed_print_timer: float = 0.0
var forward_block_timer: float = 0.0
var reverse_hold_required: float = 0.1
var reverse_hold_timer: float = 0.0
var reverse_max_speed: float = 200.0
var reverse_accel_duration: float = 1.0
var reverse_accel_time: float = 0.0
var reverse_accel_strength: float = 800.0
var braking_multiplier: float = 5.0
var braking_active: bool = false
var mass: float = 800.0
var collision_rebound: float = 0.75
var collision_rebound_layer_mask: int = 1
var collision_layer_mask: int = 1

func _cubic_bezier_y(u: float) -> float:
	var t = clamp(u, 0.0, 1.0)
	var inv = 1.0 - t
	return 3.0 * inv * inv * t * bezier_cp1y + 3.0 * inv * t * t * bezier_cp2y + t * t * t

func _physics_process(delta: float) -> void:
	acc = Vector2.ZERO
	forward_block_timer = max(forward_block_timer - delta, 0.0)
	get_input(delta)

	if throttle > 0.0:
		accel_time = min(accel_time + delta, accel_duration)
	else:
		accel_time = max(accel_time - delta, 0.0)

	if throttle < 0.0:
		reverse_accel_time = min(reverse_accel_time + delta, reverse_accel_duration)
	else:
		reverse_accel_time = max(reverse_accel_time - delta, 0.0)

	var progress = accel_time / accel_duration
	var bez = _cubic_bezier_y(progress)

	var accel_multiplier = accel_target_kmph / base_speed_kmph
	var _speed_multiplier = 1.0 + (accel_multiplier - 1.0) * bez

	if throttle > 0.0:
		acc += transform.x * accel_amount * bez * throttle
	elif throttle < 0.0:
		var rev_progress = reverse_accel_time / reverse_accel_duration
		var rev_bez = _cubic_bezier_y(rev_progress)
		acc += transform.x * (-reverse_accel_strength) * rev_bez

	app_fric(delta)
	calculate_steering(delta)

	velocity += acc * delta
	var forward_vec = transform.x.normalized()
	var signed_speed = velocity.dot(forward_vec)
	var lateral = velocity - forward_vec * signed_speed
	if throttle < 0.0 and reverse_accel_time > 0.0:
		var rev_progress = reverse_accel_time / reverse_accel_duration
		var rev_target = -reverse_max_speed * _cubic_bezier_y(rev_progress)
		var rev_rate = reverse_max_speed / reverse_accel_duration
		var ds = rev_target - signed_speed
		var step = clamp(ds, -rev_rate * delta, rev_rate * delta)
		signed_speed += step
		velocity = forward_vec * signed_speed + lateral
	else:
		if signed_speed < -reverse_max_speed:
			signed_speed = -reverse_max_speed
			velocity = forward_vec * signed_speed + lateral

	speed_print_timer += delta
	if speed_print_timer >= 1.0:
		var print_signed_speed = velocity.dot(transform.x.normalized())
		print("velocity:", print_signed_speed)
		speed_print_timer -= 1.0

	var incoming_vel = velocity

	_update_boost_timers(delta)

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

func app_fric(_delta: float) -> void:
	if velocity.length() < 0.1 and throttle == 0.0 and not boost_active:
		velocity = Vector2.ZERO
		return
	var fric_force = velocity * fric
	var drag_force = velocity * velocity.length() * drag
	if braking_active:
		var forward_vec = transform.x.normalized()
		acc += drag_force + fric_force * braking_multiplier
		var signed = velocity.dot(forward_vec)
		if signed > 0.0 and signed < 0.5:
			velocity = forward_vec * 0.0 + (velocity - forward_vec * signed)
	else:
		acc += drag_force + fric_force

func get_input(delta: float) -> void:
	var turn = 0
	if Input.is_action_pressed("ui_right"):
		turn += 1
	if Input.is_action_pressed("ui_left"):
		turn -= 1

	var speed = velocity.length()
	var normalized_speed = clamp(speed / 300.0, 0.0, 1.0)
	var steering_sensitivity = 1.0 - pow(normalized_speed, 1.05)
	var ss = max(steering_sensitivity, 0.05)
	var dynamic_steering = max_steering_angle * ss

	steer_dirn = turn * dynamic_steering

	throttle = 0.0
	if forward_block_timer <= 0.0:
		if Input.is_action_pressed("ui_up"):
			throttle += 1.0

	if Input.is_action_pressed("ui_down"):
		reverse_hold_timer += delta
		var fwd_signed = velocity.dot(transform.x.normalized())
		if fwd_signed > 0.0:
			braking_active = true
		else:
			braking_active = false
	else:
		reverse_hold_timer = 0.0
		braking_active = false

	var input_signed_speed = velocity.dot(transform.x.normalized())
	if reverse_hold_timer >= reverse_hold_required and input_signed_speed <= 0.0:
		throttle -= 1.0
		steer_dirn = steer_dirn * 1.05

	_handle_boost_input_start()

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

# ---- BOOST SYSTEM ----
var boost_input_lag: float = 0.5
var boost_duration: float = boost_input_lag * 10.0
var boost_cooldown_base: float = 10.0
var boost_strength_factor: float = 0.5
var boost_active: bool = false
var boost_available: bool = true
var boost_timer: float = 0.0
var boost_cooldown_timer: float = 0.0
var boost_pre_speed: float = 0.0
var boost_early_release_penalty: float = 10.0

func _handle_boost_input_start() -> void:
	if Input.is_key_pressed(KEY_SHIFT):
		if boost_available and not boost_active:
			_start_boost()

func _start_boost() -> void:
	boost_active = true
	boost_available = false
	boost_timer = 0.0
	boost_pre_speed = velocity.dot(transform.x.normalized())
	if boost_pre_speed > 0.001:
		velocity += transform.x.normalized() * (boost_pre_speed * boost_strength_factor)

func _update_boost_timers(delta: float) -> void:
	if boost_active:
		boost_timer += delta
		if not Input.is_key_pressed(KEY_SHIFT):
			_end_boost(true)
			return
		if boost_timer >= boost_duration:
			_end_boost(false)
			return
		var forward_vec = transform.x.normalized()
		var current_forward = velocity.dot(forward_vec)
		var target_forward = boost_pre_speed * (1.0 + boost_strength_factor)
		var approach_rate = 6.0
		var new_forward = lerp(current_forward, target_forward, clamp(approach_rate * delta, 0.0, 1.0))
		var lateral = velocity - forward_vec * current_forward
		velocity = forward_vec * new_forward + lateral

	if not boost_available:
		if boost_cooldown_timer > 0.0:
			boost_cooldown_timer = max(boost_cooldown_timer - delta, 0.0)
		else:
			boost_available = true

func _end_boost(early_release: bool) -> void:
	boost_active = false
	boost_cooldown_timer = boost_cooldown_base
	if early_release:
		boost_cooldown_timer += boost_early_release_penalty
	boost_timer = 0.0
	boost_pre_speed = 0.0
