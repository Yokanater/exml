from gymnasium.envs.registration import register
register(
	id='Driving-v0',
	entry_point='envs.driving:DrivingEnv'
)

