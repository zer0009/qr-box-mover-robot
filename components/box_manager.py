from dataclasses import dataclass
from typing import List, Dict, Optional
import logging

@dataclass
class BoxInfo:
    id: str
    contents: str
    quantity: int
    destination: str

class BoxManager:
    MAX_BOXES = 4

    def __init__(self):
        self.boxes: List[BoxInfo] = []
        self.destinations_map: Dict[str, List[BoxInfo]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def can_accept_more_boxes(self) -> bool:
        return len(self.boxes) < self.MAX_BOXES

    def has_boxes(self) -> bool:
        return len(self.boxes) > 0

    def create_box_info(self, qr_data: dict) -> Optional[BoxInfo]:
        required_fields = ['id', 'contents', 'quantity', 'destination']
        if not all(field in qr_data for field in required_fields):
            self.logger.error(f"QR data missing required fields: {qr_data}")
            return None
        
        try:
            box_info = BoxInfo(
                id=str(qr_data['id']),
                contents=str(qr_data['contents']),
                quantity=int(qr_data['quantity']),
                destination=str(qr_data['destination'])
            )
            self.logger.debug(f"Created BoxInfo: {box_info}")
            return box_info
        except (ValueError, TypeError) as e:
            self.logger.error(f"Invalid QR data format: {qr_data}, error: {e}")
            return None

    def add_box(self, box: BoxInfo) -> None:
        if self.can_accept_more_boxes():
            self.boxes.append(box)
            if box.destination not in self.destinations_map:
                self.destinations_map[box.destination] = []
            self.destinations_map[box.destination].append(box)
            self.logger.info(f"Added box {box.id} to destination {box.destination}")
        else:
            self.logger.warning("Cannot accept more boxes, maximum reached")

    def get_destinations(self) -> List[str]:
        return list(self.destinations_map.keys())

    def get_boxes_for_destination(self, destination: str) -> List[BoxInfo]:
        return self.destinations_map.get(destination, [])

    def remove_delivered_boxes(self, destination: str) -> None:
        self.boxes = [box for box in self.boxes if box.destination != destination]
        if destination in self.destinations_map:
            del self.destinations_map[destination]
            self.logger.info(f"Removed delivered boxes for destination {destination}") 