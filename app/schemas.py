from pydantic import BaseModel, Field
import datetime as dt


class Post_Readings(BaseModel):
    pulse_duration_sensor_1: float = Field(..., description="Duration of the --'sensor 1' in milliseconds")
    pulse_duration_sensor_2: float = Field(..., description="Duration of the --'sensor 2' in milliseconds")
    sensor_time: int = Field(..., description="Timestamp of the sensor reading since epoch")



class Get_Readings(BaseModel):
    timestamp: dt.datetime = Field(..., description="Timestamp of the water level recorded")
    water_level: float = Field(..., description="Water level in cm")
    water_percentage: float = Field(..., description="Water percentage in %")
    water_volume: float = Field(..., description="Water volume in liters")
    filling_time: str = Field(..., description="Filling time in MM:SS format")
    mode: str = Field(..., description="Mode of operation (Filling/Draining)")
    flag: str = Field(..., description="Leak detection flag")

class First_Reading(BaseModel):
    water_level: float = Field(..., description="By default, value is 0")
    mode: str = Field(..., description="Default mode is Draining")