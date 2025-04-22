import logging
import os
from fastapi import HTTPException
import csv
from app.config import Settings
from app.schemas import First_Reading, Get_Readings
from datetime import datetime
import pandas as pd
from app.utils import filling_time_format

#-----------------------READ DATA---------------------------
def latest_reading_read():
    try:
        file_path = os.path.join (os.getcwd(), "data", "data.csv") 
        with open(file_path, 'r') as f:
            last_row = None
            row_number = 0
            
            reader = csv.reader(f)
            for row in reader:
                last_row = row
                row_number += 1
            
            
            if row_number <= 1:
                water_level=0
                mode="FIRST"
                row_number=0

                return First_Reading(
                    water_level= water_level,
                    mode= mode
                )
            #------------------------------------
            # Defining the data columns
            Timestamp = str(last_row[0])
            Water_Level = float(last_row[1])
            Water_Percentage = float(last_row[2])
            Water_Volume = float(last_row[3])
            Filling_Time = str(filling_time_format( round(((Settings.MAX_WATER_LEVEL_CUTOFF - Water_Level)) / Settings.RATE_OF_FILLING, ndigits=1) ))
            Mode= str(last_row[4])
            # ------------------------------------

            row_number=0

            return Get_Readings(
                timestamp= Timestamp,
                water_level= Water_Level,
                water_percentage= Water_Percentage,
                water_volume= Water_Volume,
                filling_time= Filling_Time,
                mode= Mode
            )
        
    except FileNotFoundError:
        print("File not found. Please check the file path.")
        raise HTTPException(status_code=404, detail="Data file not found")
    
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while reading the data file")

# ---------------------WRITE DATA--------------------------
def latest_reading_write (values,mode,change,past_fillings, final_sensor_duration, s1, s2_c, flag):
    
    # ----------------------------
    # Defining the data columns
    Timestamp = values[0]
    Water_Level = values[1]
    Water_Percentage = values[2]
    Water_Volume = values[3]
    Final_Sensor_Duration = final_sensor_duration
    Sensor_1_Duration= s1
    Sensor_2_Duration_C= s2_c
    Mode= mode
    Change= change
    Past_Filling_Summary= past_fillings
    Flag= flag
    # ----------------------------

    try:
        file_path = os.path.join (os.getcwd(), "data", "data.csv")
        with open(file_path, 'a', newline='') as f:
            writer = csv.writer(f)      
            writer.writerow([Timestamp, Water_Level, Water_Percentage, Water_Volume, Mode, Change, Final_Sensor_Duration, Sensor_1_Duration, Sensor_2_Duration_C, Flag, Past_Filling_Summary])
            logging.info(f"Sensor to CSV succesful")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while writing to the data file")
    

#-----------------------WRITE TO PAST FILLINGS---------------------------
def past_fillings_write(values):
    try:
        file_path = os.path.join(os.getcwd(), "data", "past_fillings.csv")
        with open(file_path, 'a', newline='') as f:
            writer = csv.writer(f)      
            writer.writerow(values)
            logging.info(f"Data successfully written to Fillings CSV")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while writing to the data file")
    
#-----------------------READ PAST FILLINGS---------------------------
def past_fillings_read():
    try: 
        file_path = os.path.join(os.getcwd(), "data", "past_fillings.csv")
        with open(file_path, 'r') as f:
            last_row = None
            row_number = 0

            reader = csv.reader(f)
            for row in reader:
                last_row = row
                row_number += 1

            if row_number <= 1:
                row_number=0
                return "No past filling data available"
            #------------------------------------
            # Defining the data columns
            Start_Time = str(last_row[0])
            End_Time = str(last_row[1])
            Duration = str(last_row[2])
            Start_Level = float(last_row[3])
            End_Level = float(last_row[4])
            Water_Level_Added = float(last_row[5])
            Volume_Added = float(last_row[6])
            Rate_of_Fill = float(last_row[7])
            Minutes_Since_Filling = datetime.now() - pd.to_datetime(End_Time)
            Time_Since_Filling = filling_time_format(Minutes_Since_Filling.total_seconds()/60) # in minutes and seconds
            # ------------------------------------

            session_summary = f'{Time_Since_Filling} ago: {Water_Level_Added} cm or {Volume_Added} L added for {Duration} at {Rate_of_Fill} cm/min)'
            logging.info("Past Filling summary from CSV read successfully")
            return session_summary
   
    except FileNotFoundError:
        print("File not found. Please check the file path.")
        raise HTTPException(status_code=404, detail="Past filling file not found")


# -----------------------WRITE ALL SENSOR READINGS---------------------------
def all_sensor_readings_write(s1,s2,s2_c, time):
    Time = datetime.fromtimestamp (time).strftime("%Y-%m-%d %H:%M:%S")
    try:
        file_path = os.path.join(os.getcwd(), "data", "sensor_readings.csv")
        with open(file_path, 'a', newline='') as f:
            writer = csv.writer(f)      
            writer.writerow([ Time, s1,s2,s2_c])
            logging.info(f"Sensor readings successfully stored")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while writing to the sensor file")