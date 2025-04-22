

class Settings():
    MAX_WATER_LEVEL_CUTOFF: int = 105  # Maximum water level cutoff in cm
    MAX_WATER_LEVEL_VALIDATION: int = 114 # Maximum water level validation in cm
    TANK_VOLUME: int = 1000 # Tank volume in liters
    TANK_HEIGHT: int = 119 # Tank height in cm
    TANK_RADIUS: int = 53.4 # Tank radius in cm
    MIN_ALLOWED_FIRST_PASS_DIFFERENCE: float = 2 # Maximum allowed filling difference in cm
    MIN_ALLOWED_DIFFERENCE: float = 1 # Minimum allowed filling difference in cm
    MAX_ALLOWED_FIRST_PASS_DIFFERENCE: float = 3 # Maximum allowed filling difference in cm
    MAX_ALLOWED_DIFFERENCE: float = 2 # Maximum allowed draining difference in cm
    RATE_OF_FILLING: float = 1.2 # Rate of filling in cm/min
    MAX_TIME_TO_FILL: str = '1h,25m' # Maximum time to fill the tank from (5cm to 105cm) in hours and minutes
    MAX_TIME_BETWEEN_TWO_FILLING_SESSIONS: str = '5m' # Maximum time between two filling sessions in hours and minutes
    MAX_RETRY_COUNT: int = 2 # Maximum retry count for validation
    SENSOR_2_CALIBRATION: int = 58 # Sensor 2 calibration value in cm
    MAX_SENSOR_DISCREPANCY: int = 300 # Maximum sensor discrepancy in cm
    MAX_POSSIBLE_SENSOR_DURATION: int = 6900 # Maximum possible sensor duration in milliseconds

#GLOBAL VARIABLES
FILLING_RETRY_COUNT_DEFAULT: int = 0 # Default retry count for validation
DRAINING_RETRY_COUNT_DEFAULT: int = 0 # Default retry count for validation
SENSOR_DISCREPANCY_DEFAULT: int = 0 # Default sensor discrepancy count in cm