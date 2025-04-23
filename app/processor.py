from fastapi import HTTPException
from app.csv_handler import latest_reading_read, all_sensor_readings_write
from app.data_analysis import recent_filling_calculation
from app.config import Settings, FILLING_RETRY_COUNT_DEFAULT, DRAINING_RETRY_COUNT_DEFAULT, SENSOR_DISCREPANCY_DEFAULT
import logging
from datetime import datetime
import pandas as pd


def calculator(reading,final_sensor_duration):
    
    water_depth = round ((final_sensor_duration * 0.0343) / 2, ndigits=1)

    water_level = round (Settings.TANK_HEIGHT - water_depth, ndigits=1)
    
    water_percentage = round ((water_level / Settings.MAX_WATER_LEVEL_CUTOFF) * 100, ndigits=1)
    
    water_volume = round ((3.14 * (Settings.TANK_RADIUS ** 2) * water_level) / 1000, ndigits=1)
    
    timestamp = datetime.fromtimestamp (reading.sensor_time).strftime("%Y-%m-%d %H:%M:%S")
    
    return [timestamp, water_level, water_percentage, water_volume]


def sensor_validation(reading):
    s1= reading.pulse_duration_sensor_1
    s2= reading.pulse_duration_sensor_2
    s2_c= s2 + Settings.SENSOR_2_CALIBRATION # Calibrating the second sensor to account for the 2cm difference

    #-------------------------
    global SENSOR_DISCREPANCY_DEFAULT # Imported global variable to keep track of sensor discrepancy
    #-------------------------

    #all_sensor_readings_write(s1, s2, s2_c, reading.sensor_time)

    # Complete failure of both sensors
    if s1 == 0 and s2_c == Settings.SENSOR_2_CALIBRATION:
        logging.warning(f"Both sensor readings are zero")
        raise HTTPException(status_code=400, detail="Both sensor readings are zero")
    
    if s1 >= Settings.MAX_POSSIBLE_SENSOR_DURATION and s2_c >= (Settings.MAX_POSSIBLE_SENSOR_DURATION + Settings.SENSOR_2_CALIBRATION):
        logging.warning(f"Both sensor readings are too high >= {Settings.MAX_POSSIBLE_SENSOR_DURATION}")
        raise HTTPException(status_code=400, detail="Both sensor readings are too high >= {Settings.MAX_POSSIBLE_SENSOR_DURATION}")

    # Partial failure
    if s1 == 0 or s2_c == Settings.SENSOR_2_CALIBRATION:
        logging.warning(f'Sensors not working properly, Sensor 1: {s1} Sensor : {s2_c}')
        final_sensor_duration = s1 + s2_c
        return final_sensor_duration
    
    if s1 >=Settings.MAX_POSSIBLE_SENSOR_DURATION or s2_c >= (Settings.MAX_POSSIBLE_SENSOR_DURATION + Settings.SENSOR_2_CALIBRATION):
        logging.warning(f"Sensors not working properly, Sensor 1: {s1} Sensor 2: {s2_c}")
        final_sensor_duration = s2_c if s1 >= Settings.MAX_POSSIBLE_SENSOR_DURATION else s1
        return final_sensor_duration
       
    # If the two sensor readings differ significantly
    if abs(s1 - s2_c) > Settings.MAX_SENSOR_DISCREPANCY:
        logging.warning(f"Sensor readings differ significantly, {abs(s1 - s2_c)} -- Sensor 1: {s1} Sensor 2: {s2_c}")
        if SENSOR_DISCREPANCY_DEFAULT < Settings.MAX_RETRY_COUNT:
            SENSOR_DISCREPANCY_DEFAULT += 1
            logging.warning(f"Sensor readings differ significantly, Sensor 1: {s1} Sensor 2: {s2_c}, retry count: {SENSOR_DISCREPANCY_DEFAULT}/{Settings.MAX_RETRY_COUNT}, RETRYING...")
            raise HTTPException(status_code=400, detail=f"Sensor readings differ significantly, Sensor 1: {s1} Sensor 2: {s2_c}, retry count: {SENSOR_DISCREPANCY_DEFAULT}/{Settings.MAX_RETRY_COUNT}, RETRYING...")
        else:
            logging.warning(f"Max retry count exceeded, validation passed : ({s1} - {s2_c}) > {Settings.MAX_SENSOR_DISCREPANCY} !!")
            
    
    # If both sensors are working properly
    if s1 > s2_c:
        final_sensor_duration= round((s1*0.3) + (s2_c*0.7), ndigits=1)
        logging.info(f"Sensor 2 reading taken more into account: {s1} > {s2_c}")
    else:
        final_sensor_duration= round((s1 + s2_c) / 2, ndigits=1)
        logging.info(f"Averaging the sensor readings: {s1} and {s2_c}")
    
    logging.info('----Sensor validation passed successfully-----')
    return final_sensor_duration, s1, s2_c


def input_validation(sensor_duration):
    
    past_reading = latest_reading_read()
    latest_reading_level = round (Settings.TANK_HEIGHT - ((sensor_duration *0.0343)/2), ndigits=1)
       
    #-------------------------
    global FILLING_RETRY_COUNT_DEFAULT # Imported global variable to keep track of retry count
    global DRAINING_RETRY_COUNT_DEFAULT # Imported global variable to keep track of retry count
    global SENSOR_DISCREPANCY_DEFAULT # Imported global variable to keep track of sensor discrepancy
    #-------------------------
    
    SENSOR_DISCREPANCY_DEFAULT = 0 # Resetting the sensor discrepancy count before water level validation

    mode= None
    change=0
    past_fillings= 'NaN'
    flag= 'NaN'

    # Out of range of the tank
    if not 2< latest_reading_level <= Settings.MAX_WATER_LEVEL_VALIDATION:
        logging.warning(f"Water level [{latest_reading_level}] out of range (2-{Settings.MAX_WATER_LEVEL_VALIDATION})")
        raise HTTPException(status_code=400 ,detail=f"Water level [{latest_reading_level}] out of range (2-{Settings.MAX_WATER_LEVEL_VALIDATION})")
    
    filling_level_difference = round(latest_reading_level - past_reading.water_level, ndigits=1)
    draining_level_difference = round(past_reading.water_level - latest_reading_level,ndigits=1)
    
    logging.info(f'Incomming level difference: {filling_level_difference}')
        
# Filling tank validation
    if filling_level_difference > 0:
        logging.info('Mode --> FILLING')
        
        # Setting mode (ADJUSTING or FILLING or NaN) based on the previous reading
        if past_reading.mode == 'FIRST':
            mode= 'NaN'
        elif past_reading.mode == 'DRAINING':
            mode= 'ADJUSTING'
            logging.info('Switching to ADJUSTING mode')
        else:
            mode= 'FILLING'
        
        # First pass validation (Change in mode from draining to filling)
        if past_reading.mode == 'DRAINING':
            logging.info('Change in mode detected')
            
            if filling_level_difference <= Settings.MIN_ALLOWED_FIRST_PASS_DIFFERENCE:
                DRAINING_RETRY_COUNT_DEFAULT = 0
                FILLING_RETRY_COUNT_DEFAULT = 0
                logging.info(f"First pass filling difference too small to validate ({filling_level_difference}), minimum allowed difference: {Settings.MIN_ALLOWED_FIRST_PASS_DIFFERENCE}")
                raise HTTPException(status_code=400, detail=f"First pass filling difference too small to validate ({filling_level_difference}), minimum allowed difference: {Settings.MIN_ALLOWED_FIRST_PASS_DIFFERENCE}")

         
            if filling_level_difference > Settings.MIN_ALLOWED_FIRST_PASS_DIFFERENCE:
                
                if not FILLING_RETRY_COUNT_DEFAULT >= Settings.MAX_RETRY_COUNT:
                    FILLING_RETRY_COUNT_DEFAULT += 1
                    print(f'-------RETRY {FILLING_RETRY_COUNT_DEFAULT}----------')
                    logging.info(f"First pass filling too fast ({filling_level_difference}), retry count: {FILLING_RETRY_COUNT_DEFAULT}/{Settings.MAX_RETRY_COUNT}, RETRYING...")
                    raise HTTPException(status_code=400, detail=f"Steep filling detected: ({filling_level_difference}), retry count: {FILLING_RETRY_COUNT_DEFAULT}/{Settings.MAX_RETRY_COUNT}, RETRYING...")
                else:
                    logging.warning(f"Max retry count exceeded, validation passed : {filling_level_difference}")
                    flag= 'RED'
                    FILLING_RETRY_COUNT_DEFAULT = 0
        
        # Subsequent pass validation 
        else:
            if filling_level_difference <= Settings.MIN_ALLOWED_DIFFERENCE:
                DRAINING_RETRY_COUNT_DEFAULT = 0
                FILLING_RETRY_COUNT_DEFAULT = 0
                logging.info(f"Filling difference too small to validate ({filling_level_difference}), minimum allowed difference: {Settings.MIN_ALLOWED_DIFFERENCE}")
                raise HTTPException(status_code=400, detail=f"Filling difference too small to validate ({filling_level_difference}), minimum allowed difference: {Settings.MIN_ALLOWED_DIFFERENCE}")
            
            if filling_level_difference > Settings.MAX_ALLOWED_DIFFERENCE:
                
                if FILLING_RETRY_COUNT_DEFAULT < Settings.MAX_RETRY_COUNT:
                    FILLING_RETRY_COUNT_DEFAULT += 1
                    print(f'-------{FILLING_RETRY_COUNT_DEFAULT}----------')
                    logging.info(f"Filling too fast ({filling_level_difference}), allowed change is less than {Settings.MAX_ALLOWED_DIFFERENCE}, retry count: {FILLING_RETRY_COUNT_DEFAULT}/{Settings.MAX_RETRY_COUNT}, RETRYING...")
                    raise HTTPException(status_code=400, detail=f"Steep filling detected: ({filling_level_difference}), allowed is less than {Settings.MAX_ALLOWED_DIFFERENCE}, retry count: {FILLING_RETRY_COUNT_DEFAULT}/{Settings.MAX_RETRY_COUNT}, RETRYING...")
                else:
                    logging.warning(f"Max retry count exceeded, validation passed : {filling_level_difference}")
                    flag= 'RED'
                    FILLING_RETRY_COUNT_DEFAULT = 0

        

#Draining tank validation
    else:
        logging.info('Mode --> DRAINING')
        mode= 'DRAINING'

        # First pass validation (Change in mode from filling/adjusting to draining)
        if past_reading.mode == 'FILLING' or past_reading.mode == 'ADJUSTING':
            logging.info('Change in mode detected')
       
            if draining_level_difference <= Settings.MIN_ALLOWED_FIRST_PASS_DIFFERENCE:
                DRAINING_RETRY_COUNT_DEFAULT = 0
                FILLING_RETRY_COUNT_DEFAULT = 0
                logging.info(f"First pass draining difference too small to validate ({draining_level_difference}), minimum allowed difference: {Settings.MIN_ALLOWED_FIRST_PASS_DIFFERENCE}")
                raise HTTPException(status_code=400, detail=f"Draining difference too small to validate ({draining_level_difference}) i.e < minimum allowed difference: {Settings.MIN_ALLOWED_FIRST_PASS_DIFFERENCE}")

            
            if draining_level_difference > Settings.MAX_ALLOWED_FIRST_PASS_DIFFERENCE:
                
                if DRAINING_RETRY_COUNT_DEFAULT < Settings.MAX_RETRY_COUNT:
                    DRAINING_RETRY_COUNT_DEFAULT += 1
                    print(f'-------RETRY {DRAINING_RETRY_COUNT_DEFAULT}----------')
                    logging.info(f"First pass draining too fast ({draining_level_difference}), allowed change is less than {Settings.MAX_ALLOWED_FIRST_PASS_DIFFERENCE}, retry count: {DRAINING_RETRY_COUNT_DEFAULT}/{Settings.MAX_RETRY_COUNT}, RETRYING...")
                    raise HTTPException(status_code=400, detail=f"Draining too fast ({draining_level_difference}), allowed change is less than {Settings.MAX_ALLOWED_FIRST_PASS_DIFFERENCE}, retry count: {DRAINING_RETRY_COUNT_DEFAULT}/{Settings.MAX_RETRY_COUNT}, RETRYING...")
                else:
                    logging.warning(f"Max retry count exceeded, validation passed : {draining_level_difference}")
                    flag= 'RED'
                    DRAINING_RETRY_COUNT_DEFAULT = 0

        # Subsequent pass validation
        else:
            if draining_level_difference <= Settings.MIN_ALLOWED_DIFFERENCE:
                DRAINING_RETRY_COUNT_DEFAULT = 0
                FILLING_RETRY_COUNT_DEFAULT = 0
                logging.info(f"Draining difference too small to validate ({draining_level_difference}), minimum allowed difference: {Settings.MIN_ALLOWED_DIFFERENCE}")
                raise HTTPException(status_code=400, detail=f"Draining difference too small to validate ({draining_level_difference}) i.e < minimum allowed difference: {Settings.MIN_ALLOWED_DIFFERENCE}")

            
            if draining_level_difference > Settings.MAX_ALLOWED_DIFFERENCE:
                
                if DRAINING_RETRY_COUNT_DEFAULT < Settings.MAX_RETRY_COUNT:
                    DRAINING_RETRY_COUNT_DEFAULT += 1
                    print(f'-------RETRY {DRAINING_RETRY_COUNT_DEFAULT}----------')
                    logging.info(f"Draining too fast ({draining_level_difference}), allowed change is less than {Settings.MAX_ALLOWED_DIFFERENCE}, retry count: {DRAINING_RETRY_COUNT_DEFAULT}/{Settings.MAX_RETRY_COUNT}, RETRYING...")
                    raise HTTPException(status_code=400, detail=f"Draining too fast ({draining_level_difference}), allowed change is less than {Settings.MAX_ALLOWED_DIFFERENCE}, retry count: {DRAINING_RETRY_COUNT_DEFAULT}/{Settings.MAX_RETRY_COUNT}, RETRYING...")
                else:
                    logging.warning(f"Max retry count exceeded, validation passed : {draining_level_difference}")
                    flag= 'RED'
                    DRAINING_RETRY_COUNT_DEFAULT = 0

        # Calculating filling data         
        if past_reading.mode == 'FILLING':
            logging.info('Change in mood, FILLING to DRAINING, calculating the filling data')
            read_filling=recent_filling_calculation()

            if read_filling == 'NaN':
                logging.warning("Returning past filling record as 'NaN' as Error in past filling calculation")
                past_fillings= 'NaN'

            else:
                past_fillings= f"{read_filling[5]} cm added in ({read_filling[2]}) at {read_filling[-1]} cm/min"
    
    DRAINING_RETRY_COUNT_DEFAULT = 0
    FILLING_RETRY_COUNT_DEFAULT = 0
    
    # For first sensor reading
    if past_reading.mode != 'FIRST':
        change= filling_level_difference
    
    else:
        change= 'NaN'

  
    logging.info(f"------Water level validation successfully passed------")
    return mode,change,past_fillings,flag,past_reading.timestamp
    


