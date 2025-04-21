import logging
import os

from fastapi.responses import FileResponse
from app.security import verify_api_key
from fastapi import Depends, FastAPI, HTTPException
from app.schemas import Post_Readings
from app.csv_handler import latest_reading_read, latest_reading_write, past_fillings_read
from app.processor import calculator, input_validation


logging.basicConfig(level=logging.INFO)

app= FastAPI()

@app.get("/get_latest_reading")
def latest_reading_get(_ = Depends(verify_api_key)):
    
    #Reading from CSV
    get_reading= latest_reading_read()
    
    return get_reading


@app.post("/post_latest_reading")
def latest_reading_post(reading: Post_Readings, _ = Depends(verify_api_key)):
    
    # Averaging the sensor duration
    mean_sensor_duration= round((reading.pulse_duration_sensor_1 + reading.pulse_duration_sensor_2) / 2, ndigits=1)

    #Validation
    mode,change,past_fillings,flag=input_validation(mean_sensor_duration)
    
    #Calculation
    values=calculator(reading,mean_sensor_duration)
    
    #Writing to CSV
    latest_reading_write(values,mode,change,past_fillings, mean_sensor_duration, reading.pulse_duration_sensor_1, reading.pulse_duration_sensor_2,flag)
    
    return reading

@app.get("/past_fillings")
def past_fillings_get(_ = Depends(verify_api_key)):
    
    #Reading from CSV
    past_fillings= past_fillings_read()
    
    return past_fillings

@app.get("/files/data")
def get_data_file():
    
    file_path = os.path.join (os.getcwd(), "data", "data.csv")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, media_type='text/csv', filename="data.csv")

@app.get("/files/past_fillings")
def get_past_fillings_file():
    
    file_path = os.path.join (os.getcwd(), "data", "past_fillings.csv")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, media_type='text/csv', filename="past_fillings.csv")