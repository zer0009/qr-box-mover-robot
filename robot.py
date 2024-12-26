from components.robotic_arm import RoboticArm
from components.chassis_controller import ChassisController
from components.qr_scanner import QRScanner
from components.sensor_array import SensorArray
from components.box_manager import BoxManager
from navigation.path_planner import PathPlanner
from navigation.position import Position
from utils.exceptions import ArmError, CameraError, SensorError, NavigationError
import logging

class Robot:
    def __init__(self, config):
        self.config = config
        self.arm = RoboticArm(config.arm)
        self.chassis = ChassisController(config.chassis)
        self.qr_scanner = QRScanner(config.camera)
        self.sensors = SensorArray(config.sensors)
        self.box_manager = BoxManager()
        self.path_planner = PathPlanner(config.map)
        self.current_position = Position(x=0, y=0, theta=0.0)  # Initialize to home
        self.logger = logging.getLogger(self.__class__.__name__)

    async def initialize(self):
        """Initialize all components"""
        await self.arm.initialize()
        await self.chassis.initialize()
        await self.qr_scanner.initialize()
        await self.sensors.initialize()
        self.logger.info("Robot initialized")

    async def shutdown(self):
        """Safely shutdown all components"""
        await self.arm.shutdown()
        await self.chassis.shutdown()
        await self.qr_scanner.shutdown()
        await self.sensors.shutdown()
        self.logger.info("Robot shutdown")

    async def main_loop(self):
        while True:
            try:
                await self.check_sensors()

                if self.box_manager.can_accept_more_boxes():
                    await self.handle_pickup()
                elif self.box_manager.has_boxes():
                    await self.handle_deliveries()

                await asyncio.sleep(0.1)  # Prevent CPU hogging
            except Exception as e:
                await self.handle_error(e)

    async def check_sensors(self):
        """Monitor sensors and handle obstacles"""
        sensor_data = await self.sensors.get_readings()
        if any(distance < self.config.sensors.min_distance for distance in sensor_data.values()):
            self.logger.warning("Obstacle detected by sensors")
            await self.handle_obstacle()

    async def handle_pickup(self):
        """Handle box pickup procedure"""
        qr_data = await self.qr_scanner.scan()
        if qr_data:
            box_info = self.box_manager.create_box_info(qr_data)
            if box_info and await self.arm.pickup_box():
                self.box_manager.add_box(box_info)
                self.logger.info(f"Picked up box {box_info.id} for destination {box_info.destination}")
            else:
                self.logger.warning("Failed to pick up box")

    async def handle_deliveries(self):
        """Execute delivery routes for loaded boxes"""
        destinations = self.box_manager.get_destinations()
        route = self.path_planner.plan_multi_drop_route(destinations)

        for destination in route:
            await self.navigate_to(destination)
            await self.deliver_boxes(destination)

    async def deliver_boxes(self, destination: str):
        """Deliver boxes to the specified destination"""
        boxes = self.box_manager.get_boxes_for_destination(destination)
        if not boxes:
            self.logger.warning(f"No boxes to deliver for destination {destination}")
            return

        # Place boxes
        for box in boxes:
            if await self.arm.place_box(self.path_planner.map.get_position(destination)):
                self.logger.info(f"Delivered box {box.id} to {destination}")
            else:
                self.logger.warning(f"Failed to deliver box {box.id} to {destination}")

        self.box_manager.remove_delivered_boxes(destination)
        self.logger.info(f"All boxes delivered to {destination}")

    async def navigate_to(self, destination: str):
        """Navigate to a specific destination"""
        try:
            target_position = self.path_planner.map.get_position(destination)
            path = self.path_planner.plan_path(self.current_position, target_position)

            for waypoint in path:
                await self.move_to_waypoint(waypoint)
        except NavigationError as e:
            self.logger.error(f"Navigation to {destination} failed: {e}")
            await self.handle_obstacle()

    async def move_to_waypoint(self, waypoint: Position):
        """Move to a specific waypoint while avoiding obstacles"""
        self.logger.info(f"Moving to waypoint {waypoint}")
        # Calculate deltas
        dx = waypoint.x - self.current_position.x
        dy = waypoint.y - self.current_position.y
        dtheta = waypoint.theta - self.current_position.theta

        # Send movement command
        await self.chassis.move_towards(dx, dy, dtheta)
        self.current_position = waypoint
        self.logger.info(f"Arrived at waypoint {waypoint}")

    async def handle_obstacle(self):
        """Handle obstacle presence"""
        self.logger.warning("Handling obstacle")
        # Implement obstacle handling, e.g., re-route
        # For simplicity, stop and attempt to replan
        await self.chassis.stop()
        await asyncio.sleep(1)  # Wait before retrying
        self.logger.info("Attempting to replan path")
        # Additional obstacle handling logic can be implemented here

    async def handle_error(self, error: Exception):
        """Handle various error conditions"""
        try:
            # Log the error
            self.logger.error(f"Error occurred: {error}")

            # Stop all movement
            await self.chassis.stop()

            # Move arm to home position
            await self.arm._home()

            # Check sensors
            sensor_readings = await self.sensors.get_readings()
            if any(reading < self.config.sensors.min_distance for reading in sensor_readings.values()):
                await self.handle_obstacle()

            # Try to reinitialize problematic component
            if isinstance(error, ArmError):
                await self.arm.initialize()
            elif isinstance(error, CameraError):
                await self.qr_scanner.initialize()
            elif isinstance(error, SensorError):
                await self.sensors.initialize()
            elif isinstance(error, NavigationError):
                self.logger.error("Navigation error encountered. Manual intervention might be required.")
        except Exception as recovery_error:
            self.logger.critical(f"Error recovery failed: {recovery_error}")
            await self.shutdown()
            raise 