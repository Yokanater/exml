def forward(car):
    car.accelerate(1.0)

def back(car):
    car.accelerate(-1.0)

def steer_right(car, amount=10):
    car.steer(amount)

def steer_left(car, amount=10):
    car.steer(-amount)
