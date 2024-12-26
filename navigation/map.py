from typing import Dict, List, Tuple
import numpy as np
import json
from navigation.position import Position
import logging
from utils.exceptions import NavigationError

class Map:
    def __init__(self, config):
        self.width = config.width
        self.height = config.height
        self.grid = np.zeros((self.height, self.width), dtype=np.int8)
        self.locations = {}  # Named locations and their positions
        self.logger = logging.getLogger(self.__class__.__name__)
        self._load_map(config.map_file)

    def _load_map(self, map_file: str):
        """Load map from file"""
        try:
            with open(map_file, 'r') as f:
                map_data = json.load(f)
            
            obstacles = map_data.get('obstacles', [])
            for obs in obstacles:
                x = int(obs['x'])
                y = int(obs['y'])
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.grid[y, x] = 1  # 1 indicates obstacle
            self.logger.info(f"Loaded {len(obstacles)} obstacles into the map")

            locations = map_data.get('locations', {})
            for name, pos in locations.items():
                self.locations[name] = Position(x=pos['x'], y=pos['y'], theta=0.0)
            self.logger.info(f"Loaded {len(self.locations)} locations into the map")
        except FileNotFoundError:
            self.logger.error(f"Map file {map_file} not found")
            raise NavigationError(f"Map file {map_file} not found")
        except (ValueError, KeyError) as e:
            self.logger.error(f"Invalid map file format: {e}")
            raise NavigationError(f"Invalid map file format: {e}")

    def get_position(self, location_name: str) -> Position:
        """Get position for named location"""
        pos = self.locations.get(location_name)
        if pos is None:
            self.logger.error(f"Location {location_name} not found in map")
            raise NavigationError(f"Location {location_name} not found in map")
        return pos

    def is_valid_position(self, position: Position) -> bool:
        """Check if position is valid and obstacle-free"""
        x, y = int(position.x), int(position.y)
        if 0 <= x < self.width and 0 <= y < self.height:
            valid = self.grid[y, x] == 0
            if not valid:
                self.logger.debug(f"Position {position} is invalid (obstacle)")
            return valid
        self.logger.debug(f"Position {position} is out of map bounds")
        return False 