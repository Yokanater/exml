extends Area2D

@export var total_laps: int = 3
@export var checkpoints: Array[Area2D] = [] 

var car_inside := false
var has_started := {}
var lap_count := {}
var checkpoints_passed := {} 

signal lap_completed(current_lap: int, car_id: int)

func _ready():
	connect("body_entered", Callable(self, "_on_body_entered"))
	
	connect("body_exited", Callable(self, "_on_body_exited"))
	
	for i in range(checkpoints.size()):
		if checkpoints[i]:
			checkpoints[i].connect("body_entered", Callable(self, "_on_checkpoint_entered").bind(i))

func _on_checkpoint_entered(body, checkpoint_index: int):
	if body is CharacterBody2D:
		var car_id = body.car_id
		
		if not checkpoints_passed.has(car_id):
			checkpoints_passed[car_id] = []
		
		if checkpoint_index not in checkpoints_passed[car_id]:
			checkpoints_passed[car_id].append(checkpoint_index)
			
			print("Car [", car_id, "] passed checkpoint ", checkpoint_index + 1)

func _on_body_entered(body):
	if body is CharacterBody2D:
		if not car_inside:
			
			car_inside = true
			
			var car_id = body.car_id
			
			if not lap_count.has(car_id):
				lap_count[car_id] = 0
				checkpoints_passed[car_id] = []
			
			body.total_laps = total_laps
			
			body.current_lap = lap_count[car_id]
			
			if not has_started.has(car_id):
				has_started[car_id] = true
				checkpoints_passed[car_id] = []
				print("Car [", car_id, "] crossed start line — race started.")
				return
			
			var all_passed = checkpoints_passed[car_id].size() == checkpoints.size()
			
			if all_passed:
				lap_count[car_id] += 1
				
				body.current_lap = lap_count[car_id]
				
				emit_signal("lap_completed", lap_count[car_id], car_id)
				print("Lap completed by Car [", car_id, "] | Lap:", lap_count[car_id])
				
				if lap_count[car_id] >= total_laps:
					print("Car [", car_id, "] has completed all laps")
					_race_finished(car_id)
				
				checkpoints_passed[car_id] = []
			else:
				var missed = checkpoints.size() - checkpoints_passed[car_id].size()
				
				print("Car [", car_id, "] missed ", missed, " checkpoint(s)!")

func _on_body_exited(body):
	if body is CharacterBody2D:
		car_inside = false

func _race_finished(car_id: int):
	pass
