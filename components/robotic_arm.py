import asyncio
from typing import Tuple
import serial_asyncio
from utils.exceptions import ArmError
import logging

class ArmProtocol(asyncio.Protocol):
    def __init__(self, loop, future):
        self.loop = loop
        self.future = future
        self.buffer = ''
        self.logger = logging.getLogger(self.__class__.__name__)

    def connection_made(self, transport):
        self.transport = transport
        self.logger.info("Serial connection made to robotic arm")

    def data_received(self, data):
        self.buffer += data.decode()
        if '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            self.logger.debug(f"Received data: {line}")
            if not self.future.done():
                self.future.set_result(line)

    def connection_lost(self, exc):
        if exc:
            self.logger.error(f"Serial connection lost: {exc}")
            if not self.future.done():
                self.future.set_exception(exc)
        else:
            self.logger.info("Serial connection closed")
            if not self.future.done():
                self.future.set_result(None)

class RoboticArm:
    def __init__(self, config):
        self.config = config
        self.transport = None
        self.protocol = None
        self.position = (0, 0, 0)  # x, y, z coordinates
        self.is_gripper_closed = False
        self.logger = logging.getLogger(self.__class__.__name__)

    async def initialize(self):
        """Initialize serial connection to uArm"""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        try:
            self.transport, self.protocol = await serial_asyncio.create_serial_connection(
                loop, lambda: ArmProtocol(loop, future), self.config.port, baudrate=self.config.baudrate
            )
            await self._home()
            self.logger.info("RoboticArm initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize RoboticArm: {e}")
            raise ArmError(f"Failed to initialize RoboticArm: {e}")

    async def shutdown(self):
        """Safely return to home position and close connection"""
        try:
            await self._home()
        except Exception as e:
            self.logger.error(f"Error moving to home during shutdown: {e}")
        if self.transport:
            self.transport.close()
            self.transport = None
            self.protocol = None
        self.logger.info("RoboticArm shutdown")

    async def pickup_box(self) -> bool:
        """Complete pickup sequence for a box"""
        try:
            await self._move_to_pickup_position()
            await self._close_gripper()
            if await self._check_grip():
                await self._move_to_storage_position()
                return True
            return False
        except ArmError as e:
            self.logger.error(f"Pickup failed: {e}")
            await self._home()
            return False

    async def place_box(self, position: Tuple[float, float, float]) -> bool:
        """Place box at specified position"""
        try:
            await self._move_to_position(position)
            await self._open_gripper()
            await self._move_up()
            return True
        except ArmError as e:
            self.logger.error(f"Place failed: {e}")
            return False

    async def _home(self):
        """Move arm to home position"""
        await self._send_command("M2019")  # Home command
        self.position = tuple(self.config.home_position)
        self.logger.info("Robotic arm moved to home position")

    async def _move_to_position(self, position: Tuple[float, float, float]):
        """Move to absolute position"""
        x, y, z = position
        command = f"G0 X{x} Y{y} Z{z}"
        await self._send_command(command)
        self.position = position
        self.logger.info(f"Robotic arm moved to position {position}")

    async def _close_gripper(self):
        """Close gripper"""
        await self._send_command("M2231")  # Close gripper
        self.is_gripper_closed = True
        self.logger.info("Robotic arm gripper closed")

    async def _open_gripper(self):
        """Open gripper"""
        await self._send_command("M2232")  # Open gripper
        self.is_gripper_closed = False
        self.logger.info("Robotic arm gripper opened")

    async def _check_grip(self) -> bool:
        """Check if box is properly gripped"""
        # Placeholder for actual sensor check
        self.logger.debug("Checking grip status")
        await asyncio.sleep(0.1)
        return True  # Assuming always true for now

    async def _move_to_pickup_position(self):
        """Move arm to pickup position"""
        pickup_position = tuple(self.config.pickup_position)
        await self._move_to_position(pickup_position)
        self.logger.info("Robotic arm moved to pickup position")

    async def _move_to_storage_position(self):
        """Move arm to storage position"""
        storage_position = tuple(self.config.storage_position)
        await self._move_to_position(storage_position)
        self.logger.info("Robotic arm moved to storage position")

    async def _move_up(self):
        """Move arm up after placing"""
        x, y, z = self.position
        # Assuming moving up increases z by a certain amount, say 50
        new_z = z + 50
        await self._move_to_position((x, y, new_z))
        self.logger.info("Robotic arm moved up after placing")

    async def _send_command(self, command: str) -> str:
        """Send command to arm and wait for response"""
        if not self.transport or not self.protocol:
            self.logger.error("Arm not initialized")
            raise ArmError("Arm not initialized")

        future_response = asyncio.get_running_loop().create_future()
        self.protocol.future = future_response

        self.transport.write(f"{command}\n".encode())
        self.logger.debug(f"Sent command: {command}")

        try:
            response = await asyncio.wait_for(future_response, timeout=2.0)
            self.logger.debug(f"Received response: {response}")
            if response and "error" in response.lower():
                raise ArmError(f"Command failed: {response}")
            return response
        except asyncio.TimeoutError:
            self.logger.error("Timeout waiting for arm response")
            raise ArmError("Timeout waiting for arm response")
        except Exception as e:
            self.logger.error(f"Error receiving response: {e}")
            raise ArmError(f"Error receiving response: {e}") 