from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Position:
    x: float
    y: float
    theta: float  # Orientation in radians
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate Euclidean distance to another position"""
        return math.sqrt(
            (self.x - other.x) ** 2 + 
            (self.y - other.y) ** 2
        )
        
    def angle_to(self, other: 'Position') -> float:
        """Calculate angle to another position"""
        return math.atan2(
            other.y - self.y,
            other.x - self.x
        ) 