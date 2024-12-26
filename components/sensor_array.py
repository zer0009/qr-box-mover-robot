import RPi.GPIO as GPIO
import time
from typing import List, Dict, Optional
import asyncio
import logging
from utils.exceptions import SensorError

class SensorArray:
    def __init__(self, config):
        self.sensors = {}
        for position, pins in config.sensor_pins.items():
            self.sensors[position] = UltrasonicSensor(
                trigger_pin=pins.trigger,
                echo_pin=pins.echo
            )
        self.min_distance = config.min_distance
        self.logger = logging.getLogger(self.__class__.__name__)

    async def initialize(self):
        """Initialize GPIO for all sensors"""
        GPIO.setmode(GPIO.BCM)
        for sensor in self.sensors.values():
            sensor.setup()
        self.logger.info("SensorArray initialized")

    async def shutdown(self):
        """Cleanup GPIO"""
        GPIO.cleanup()
        self.logger.info("SensorArray shutdown")

    async def get_readings(self) -> Dict[str, float]:
        """Get readings from all sensors"""
        tasks = []
        for position, sensor in self.sensors.items():
            tasks.append(sensor.measure_distance())
        
        distances = await asyncio.gather(*tasks, return_exceptions=True)
        readings = {}
        for position, distance in zip(self.sensors.keys(), distances):
            if isinstance(distance, Exception):
                self.logger.error(f"Error reading sensor {position}: {distance}")
                readings[position] = float('inf')  # Treat as no obstacle
            else:
                readings[position] = distance
        self.logger.debug(f"Sensor readings: {readings}")
        return readings

    async def is_path_clear(self) -> bool:
        """Check if path is clear of obstacles"""
        readings = await self.get_readings()
        return all(distance > self.min_distance for distance in readings.values())

class UltrasonicSensor:
    def __init__(self, trigger_pin: int, echo_pin: int):
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.logger = logging.getLogger(self.__class__.__name__)

    def setup(self):
        """Setup GPIO pins"""
        GPIO.setup(self.trigger_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        GPIO.output(self.trigger_pin, GPIO.LOW)
        self.logger.debug(f"UltrasonicSensor setup on Trigger {self.trigger_pin}, Echo {self.echo_pin}")

    async def measure_distance(self) -> float:
        """Measure distance in centimeters"""
        try:
            # Send trigger pulse
            GPIO.output(self.trigger_pin, GPIO.HIGH)
            await asyncio.sleep(0.00001)  # 10 microseconds
            GPIO.output(self.trigger_pin, GPIO.LOW)

            # Wait for echo start
            pulse_start = await self._wait_for_signal(GPIO.HIGH, timeout=0.02)
            if pulse_start is None:
                self.logger.warning("No echo received (start)")
                return float('inf')

            # Wait for echo end
            pulse_end = await self._wait_for_signal(GPIO.LOW, timeout=0.02)
            if pulse_end is None:
                self.logger.warning("No echo received (end)")
                return float('inf')

            # Calculate distance
            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17150  # Speed of sound (cm/s) / 2
            distance = round(distance, 2)
            self.logger.debug(f"Measured distance: {distance} cm")
            return distance
        except Exception as e:
            self.logger.error(f"Error measuring distance: {e}")
            return float('inf')

    async def _wait_for_signal(self, level: int, timeout: float) -> Optional[float]:
        """Wait for GPIO input to reach a level with timeout"""
        start_time = time.time()
        while GPIO.input(self.echo_pin) != level:
            if time.time() - start_time > timeout:
                return None
            await asyncio.sleep(0.0001)  # 100 microseconds
        return time.time() 