from typing import List, Tuple, Optional, Dict
import numpy as np
from navigation.position import Position
from navigation.map import Map
from utils.exceptions import NavigationError
import math
import logging

class PathPlanner:
    def __init__(self, map_config):
        self.map = Map(map_config)
        self.logger = logging.getLogger(self.__class__.__name__)

    def plan_multi_drop_route(self, destinations: List[str]) -> List[str]:
        """Optimize the order of destinations for efficient delivery using Nearest Neighbor TSP"""
        if not destinations:
            return []

        current_pos = Position(x=0, y=0, theta=0.0)  # Starting at home or current position
        remaining = destinations.copy()
        route = []

        while remaining:
            nearest = min(remaining, key=lambda x: self._distance_to(current_pos, x))
            route.append(nearest)
            current_pos = self.map.get_position(nearest)
            remaining.remove(nearest)

        self.logger.info(f"Planned multi-drop route: {route}")
        return route

    def plan_path(self, start: Position, end: Position) -> List[Position]:
        """Implement A* pathfinding between two points"""
        path = self._a_star(start, end)
        if not path:
            self.logger.error(f"No path found from {start} to {end}")
            raise NavigationError(f"No path found from {start} to {end}")
        smoothed_path = self._smooth_path(path)
        self.logger.debug(f"Planned path with {len(smoothed_path)} waypoints")
        return smoothed_path

    def _distance_to(self, pos: Position, destination: str) -> float:
        dest_pos = self.map.get_position(destination)
        return pos.distance_to(dest_pos)

    def _a_star(self, start: Position, goal: Position) -> Optional[List[Position]]:
        """A* pathfinding implementation using grid-based A*"""
        def heuristic(a: Position, b: Position) -> float:
            return a.distance_to(b)

        start_cell = (int(start.x), int(start.y))
        goal_cell = (int(goal.x), int(goal.y))

        open_set = set()
        open_set.add(start_cell)

        came_from = {}

        g_score = {start_cell: 0}
        f_score = {start_cell: heuristic(start, goal)}

        while open_set:
            current = min(open_set, key=lambda cell: f_score.get(cell, float('inf')))
            current_pos = Position(x=current[0], y=current[1], theta=0.0)

            if current == goal_cell:
                return self._reconstruct_path(came_from, current)

            open_set.remove(current)
            neighbors = self._get_neighbors(current)

            for neighbor in neighbors:
                tentative_g_score = g_score[current] + current_pos.distance_to(Position(x=neighbor[0], y=neighbor[1], theta=0.0))

                if tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    neighbor_pos = Position(x=neighbor[0], y=neighbor[1], theta=0.0)
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor_pos, goal)
                    if neighbor not in open_set:
                        open_set.add(neighbor)

        # No path found
        self.logger.warning(f"No path found from {start} to {goal}")
        return None  

    def _reconstruct_path(self, came_from: Dict[Tuple[int, int], Tuple[int, int]], current: Tuple[int, int]) -> List[Position]:
        total_path = [current]
        while current in came_from:
            current = came_from[current]
            total_path.append(current)
        total_path.reverse()
        path_positions = [Position(x=pos[0], y=pos[1], theta=0.0) for pos in total_path]
        self.logger.debug(f"Reconstructed path: {path_positions}")
        return path_positions

    def _get_neighbors(self, current: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get traversable neighboring cells (4-directional)"""
        directions = [(-1,0), (1,0), (0,-1), (0,1)]  # left, right, up, down
        neighbors = []
        for dx, dy in directions:
            neighbor = (current[0] + dx, current[1] + dy)
            if self.map.is_valid_position(Position(x=neighbor[0], y=neighbor[1], theta=0.0)):
                neighbors.append(neighbor)
        return neighbors

    def _smooth_path(self, path: List[Position]) -> List[Position]:
        """Simplify the path by removing unnecessary waypoints"""
        if not path:
            return path
        smoothed_path = [path[0]]
        current_angle = path[0].theta

        for i in range(1, len(path)):
            prev = smoothed_path[-1]
            current = path[i]
            desired_angle = math.atan2(current.y - prev.y, current.x - prev.x)
            if abs(desired_angle - current_angle) > 0.1:  # threshold angle in radians
                smoothed_path.append(current)
                current_angle = desired_angle
        if path[-1] != smoothed_path[-1]:
            smoothed_path.append(path[-1])
        self.logger.debug(f"Smoothed path from {len(path)} to {len(smoothed_path)} waypoints")
        return smoothed_path 