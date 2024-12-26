from typing import Tuple
import asyncio
from navigation.position import Position
import RPi.GPIO as GPIO
import logging

class ChassisController:
    def __init__(self, config):
        self.config = config
        self.motors = {
            'front_left': Motor(config.pins['front_left']),
            'front_right': Motor(config.pins['front_right']),
            'back_left': Motor(config.pins['back_left']),
            'back_right': Motor(config.pins['back_right'])
        }
        self.logger = logging.getLogger(self.__class__.__name__)

    async def initialize(self):
        """Initialize GPIO and motor controllers"""
        GPIO.setmode(GPIO.BCM)
        for motor in self.motors.values():
            motor.setup()
        self.logger.info("ChassisController initialized")

    async def shutdown(self):
        """Stop all motors and cleanup GPIO"""
        for motor in self.motors.values():
            motor.stop()
        GPIO.cleanup()
        self.logger.info("ChassisController shutdown")

    async def move_towards(self, dx: float, dy: float, dtheta: float):
        """Move chassis towards target deltas"""
        # Calculate wheel velocities for holonomic drive
        velocities = self._calculate_wheel_velocities(dx, dy, dtheta)
        self._set_motor_speeds(velocities)
        self.logger.debug(f"Set motor speeds: {velocities}")

    def _calculate_wheel_velocities(self, dx: float, dy: float, angle: float) -> dict:
        """Calculate individual wheel velocities for holonomic movement"""
        # Simple mecanum wheel formulas
        front_left = dx + dy + angle
        front_right = dx - dy - angle
        back_left = dx - dy + angle
        back_right = dx + dy - angle

        # Normalize wheel speeds
        max_velocity = max(abs(front_left), abs(front_right), abs(back_left), abs(back_right), 1)
        front_left /= max_velocity
        front_right /= max_velocity
        back_left /= max_velocity
        back_right /= max_velocity

        return {
            'front_left': front_left,
            'front_right': front_right,
            'back_left': back_left,
            'back_right': back_right
        }

    def _set_motor_speeds(self, velocities: dict):
        """Set speeds for all motors"""
        for motor_name, velocity in velocities.items():
            self.motors[motor_name].set_speed(velocity)
        self.logger.debug(f"Motor speeds set: {velocities}")

    async def stop(self):
        """Stop all motors"""
        for motor in self.motors.values():
            motor.stop()
        self.logger.info("ChassisController stopped all motors")

class Motor:
    def __init__(self, pins):
        self.pwm_pin = pins.pwm
        self.dir_pin = pins.dir
        self.pwm = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def setup(self):
        """Setup GPIO pins for motor"""
        GPIO.setup(self.pwm_pin, GPIO.OUT)
        GPIO.setup(self.dir_pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pwm_pin, 1000)  # 1000Hz frequency
        self.pwm.start(0)
        self.logger.debug(f"Motor setup on PWM pin {self.pwm_pin}, DIR pin {self.dir_pin}")

    def set_speed(self, speed: float):
        """Set motor speed and direction"""
        if self.pwm is None:
            self.logger.error("PWM not initialized")
            return
        direction = GPIO.HIGH if speed >= 0 else GPIO.LOW
        GPIO.output(self.dir_pin, direction)
        duty_cycle = min(max(abs(speed), 0), 100)  # Clamp to 0-100
        self.pwm.ChangeDutyCycle(duty_cycle)
        self.logger.debug(f"Set motor {self.pwm_pin} speed to {duty_cycle}% {'CW' if direction == GPIO.HIGH else 'CCW'}")

    def stop(self):
        """Stop motor"""
        if self.pwm:
            self.pwm.ChangeDutyCycle(0)
            self.logger.debug(f"Motor on PWM pin {self.pwm_pin} stopped") 