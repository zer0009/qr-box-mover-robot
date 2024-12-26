class ArmError(Exception):
    """Exception raised for errors in the robotic arm operations."""
    pass

class CameraError(Exception):
    """Exception raised for camera related errors."""
    pass

class SensorError(Exception):
    """Exception raised for sensor related errors."""
    pass

class NavigationError(Exception):
    """Exception raised for navigation related errors."""
    pass 