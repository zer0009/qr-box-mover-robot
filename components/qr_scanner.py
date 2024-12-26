import cv2
from pyzbar.pyzbar import decode
import numpy as np
import json
from typing import Optional, Dict
import asyncio
import logging
from utils.exceptions import CameraError

class QRScanner:
    def __init__(self, config):
        self.config = config
        self.camera = None
        self.logger = logging.getLogger(self.__class__.__name__)

    async def initialize(self):
        """Initialize camera"""
        self.camera = cv2.VideoCapture(self.config.camera_id)
        if not self.camera.isOpened():
            self.logger.error("Failed to open camera")
            raise CameraError("Failed to open camera")
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.resolution[0])
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.resolution[1])
        self.logger.info("QRScanner initialized")

    async def shutdown(self):
        """Release camera resources"""
        if self.camera:
            self.camera.release()
            self.camera = None
            self.logger.info("QRScanner shutdown")

    async def scan(self) -> Optional[Dict]:
        """Scan for QR code and return decoded data"""
        if not self.camera:
            self.logger.error("Camera not initialized")
            return None

        # Run the blocking read in a separate thread
        ret, frame = await asyncio.to_thread(self.camera.read)
        if not ret:
            self.logger.warning("Failed to read frame from camera")
            return None

        # Process frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        decoded_objects = decode(gray)

        for obj in decoded_objects:
            try:
                # Assuming QR code contains JSON data
                data = json.loads(obj.data.decode('utf-8'))
                if self._validate_qr_data(data):
                    self.logger.info(f"Decoded QR data: {data}")
                    return data
            except json.JSONDecodeError:
                self.logger.warning(f"Failed to decode QR data: {obj.data}")
                continue

        self.logger.debug("No valid QR code found")
        return None

    def _validate_qr_data(self, data: Dict) -> bool:
        """Validate QR code data format"""
        required_fields = ['id', 'contents', 'quantity', 'destination']
        valid = all(field in data for field in required_fields)
        if not valid:
            self.logger.warning(f"QR data missing required fields: {data}")
        return valid 