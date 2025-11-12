def forward(car):
    car.accelerate(1.0)

def back(car):
    car.accelerate(-1.0)

def steer_right(car, amount=10):
    car.steer(amount)

def steer_left(car, amount=10):
    car.steer(-amount)

def brake(car, strength=0.6):
    car.brake(strength)

