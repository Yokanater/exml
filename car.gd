extends CharacterBody2D

var max_speed = 200
var acceleration = 500
var friction = 400
var speed_print_timer: float = 0.0

func _physics_process(delta):
	var input_dir = Vector2.ZERO

	if Input.is_action_pressed("ui_right"):
		input_dir.x += 1
	if Input.is_action_pressed("ui_left"):
		input_dir.x -= 1
	if Input.is_action_pressed("ui_down"):
		input_dir.y += 1
	if Input.is_action_pressed("ui_up"):
		input_dir.y -= 1

	if input_dir.length() > 0:
		input_dir = input_dir.normalized()
		velocity = velocity.move_toward(input_dir * max_speed, acceleration * delta)
	else:
		velocity = velocity.move_toward(Vector2.ZERO, friction * delta)

	move_and_slide()
