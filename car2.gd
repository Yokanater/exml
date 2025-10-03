extends CharacterBody2D

var wheelbase: float = 170.0
var max_steering_angle: float = deg_to_rad(120.0) # in radians for rotation
var steer_dirn: float = 0.0
var acc = Vector2.ZERO
var fric = -0.98
var drag = -0.001
var braking = -450
var maxrspeed= 250

func _physics_process(delta: float) -> void:
	acc = Vector2.ZERO
	get_input()
	app_fric()
	calculate_steering(delta)
	velocity += acc * delta
	move_and_slide()

func app_fric():
	if velocity.length() <5:
		velocity = Vector2.ZERO
	var fric_force = velocity*fric
	var drag_force = velocity*velocity.length()*drag
	acc += drag_force + fric_force

func get_input():
	var turn = 0
	if Input.is_action_pressed("ui_right"):
		turn += 1
	if Input.is_action_pressed("ui_left"):
		turn -= 1

	var speed = velocity.length()
	var max_speed = 1000.0  # Adjust this to match your game's max expected speed

	# Steering sensitivity factor: lower at high speed
	var speed_factor = clamp(1.0 / (1.0 + (speed / 200.0)), 0.1, 1.0)

	var dynamic_steering = max_steering_angle * speed_factor
	steer_dirn = turn * dynamic_steering

	if Input.is_action_pressed("ui_up"):
		acc = transform.x * 800  # forward in local x-axis
	if Input.is_action_pressed("ui_down"):
		acc = -(transform.x * 800)

func calculate_steering(delta: float) -> void:
	var rw = position - transform.x * (wheelbase / 2.0)
	var fw = position + transform.x * (wheelbase / 2.0)

	rw += velocity * delta
	fw += velocity.rotated(steer_dirn) * delta

	var new_dirn = (fw - rw).normalized()

	if velocity.length() > 5.0: # <-- avoid corrections at low speed
		var d = new_dirn.dot(velocity.normalized())
		if d > 0:
			velocity = new_dirn * velocity.length()
		elif d < 0:
			velocity = -new_dirn * min(velocity.length(), maxrspeed)
	else:
		# At very low speed, just align with input steering
		velocity = new_dirn * velocity.length()

	rotation = new_dirn.angle()
