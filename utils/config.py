import yaml
from dataclasses import dataclass
from typing import Dict

@dataclass
class ArmConfig:
    port: str
    baudrate: int
    home_position: list  # [x, y, z]
    pickup_height: float
    pickup_position: list  # [x, y, z]
    storage_position: list  # [x, y, z]

@dataclass
class ChassisPins:
    pwm: int
    dir: int

@dataclass
class ChassisConfig:
    pins: Dict[str, ChassisPins]

@dataclass
class CameraConfig:
    camera_id: int
    resolution: list  # [width, height]

@dataclass
class SensorPins:
    trigger: int
    echo: int

@dataclass
class SensorsConfig:
    min_distance: float
    sensor_pins: Dict[str, SensorPins]

@dataclass
class MapConfig:
    width: int
    height: int
    map_file: str

@dataclass
class RobotConfig:
    arm: ArmConfig
    chassis: ChassisConfig
    camera: CameraConfig
    sensors: SensorsConfig
    map: MapConfig

def load_config(config_file: str = 'config.yaml') -> RobotConfig:
    """Load configuration from YAML file"""
    with open(config_file, 'r') as f:
        config_data = yaml.safe_load(f)
    
    # Convert dict to dataclasses
    arm_config = ArmConfig(**config_data['arm'])
    chassis_pins = {k: ChassisPins(**v) for k, v in config_data['chassis']['pins'].items()}
    chassis_config = ChassisConfig(pins=chassis_pins)
    camera_config = CameraConfig(**config_data['camera'])
    sensor_pins = {k: SensorPins(**v) for k, v in config_data['sensors']['sensor_pins'].items()}
    sensors_config = SensorsConfig(
        min_distance=config_data['sensors']['min_distance'],
        sensor_pins=sensor_pins
    )
    map_config = MapConfig(**config_data['map'])
    
    return RobotConfig(
        arm=arm_config,
        chassis=chassis_config,
        camera=camera_config,
        sensors=sensors_config,
        map=map_config
    ) 