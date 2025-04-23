import logging
import os

from fastapi.responses import FileResponse
from app.data_analysis import leak_check
from app.security import verify_api_key
from fastapi import Depends, FastAPI, HTTPException
from app.schemas import Post_Readings
from app.csv_handler import latest_reading_read, latest_reading_write, past_fillings_read
from app.processor import calculator, input_validation, sensor_validation


logging.basicConfig(level=logging.INFO)

app= FastAPI()

@app.get("/get_latest_reading")
def latest_reading_get(_ = Depends(verify_api_key)):
    
    #Reading from CSV
    get_reading= latest_reading_read()
    
    return get_reading


@app.post("/post_latest_reading")
def latest_reading_post(reading: Post_Readings, _ = Depends(verify_api_key)):
    
    # Validating and averaging the sensor duration
    final_sensor_duration, s1, s2_c= sensor_validation(reading)

    # Validation
    mode,change,past_fillings,flag,past_reading_time=input_validation(final_sensor_duration)
    
    # Calculation
    values=calculator(reading,final_sensor_duration)
   
    # Leak check
    logging.info("Checking for leak...")
    leak= leak_check(past_reading_time, values[0])
    
    # Writing to CSV
    latest_reading_write(values,mode,change,past_fillings, final_sensor_duration, s1, s2_c,flag,leak)
  

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

@app.get("/files/sensor_readings")
def get_sensor_readings_file():
    
    file_path = os.path.join (os.getcwd(), "data", "sensor_readings.csv")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, media_type='text/csv', filename="sensor_readings.csv")