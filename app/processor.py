from fastapi import HTTPException
from app.csv_handler import latest_reading_read, all_sensor_readings_write
from app.data_analysis import past_filling_read
from app.config import Settings, FILLING_RETRY_COUNT_DEFAULT, DRAINING_RETRY_COUNT_DEFAULT, SENSOR_DISCREPANCY_DEFAULT
import logging
from datetime import datetime


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

    all_sensor_readings_write(s1, s2, s2_c, reading.sensor_time)

    # Complete failure of both sensors
    if s1 == 0 and s2_c == Settings.SENSOR_2_CALIBRATION:
        raise HTTPException(status_code=400, detail="Both sensor readings are zero")
    
    if s1 >= Settings.MAX_POSSIBLE_SENSOR_DURATION and s2_c >= (Settings.MAX_POSSIBLE_SENSOR_DURATION + Settings.SENSOR_2_CALIBRATION):
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
        logging.warning(f"Sensor readings differ significantly, Sensor 1: {s1} Sensor 2: {s2_c}")
        if SENSOR_DISCREPANCY_DEFAULT < Settings.MAX_RETRY_COUNT:
            SENSOR_DISCREPANCY_DEFAULT += 1
            raise HTTPException(status_code=400, detail=f"Sensor readings differ significantly, Sensor 1: {s1} Sensor 2: {s2_c}, retry count: {SENSOR_DISCREPANCY_DEFAULT}/{Settings.MAX_RETRY_COUNT}, RETRYING...")
        else:
            logging.warning(f"Max retry count exceeded, validation passed : ({s1} - {s2_c}) > {Settings.MAX_SENSOR_DISCREPANCY} !!")
            
    
    # If both sensors are working properly
    if s1 > s2_c:
        final_sensor_duration= round((s1*0.3) + (s2_c*0.7), ndigits=1)
    else:
        final_sensor_duration= round((s1 + s2_c) / 2, ndigits=1)
    
    
    return final_sensor_duration, s1, s2_c


def input_validation(sensor_duration):
    logging.info('Starting input validation')
    last_reading = latest_reading_read()
    latest_reading_level = round (Settings.TANK_HEIGHT - ((sensor_duration *0.0343)/2), ndigits=1)
    logging.info(f'Incoming level: {latest_reading_level}')
   
    #-------------------------
    global FILLING_RETRY_COUNT_DEFAULT # Imported global variable to keep track of retry count
    global DRAINING_RETRY_COUNT_DEFAULT # Imported global variable to keep track of retry count
    global SENSOR_DISCREPANCY_DEFAULT # Imported global variable to keep track of sensor discrepancy
    #-------------------------
    
    mode= None
    change=0
    past_fillings= 'NaN'
    flag= 'NaN'

    if not 2< latest_reading_level <= Settings.MAX_WATER_LEVEL_VALIDATION:
        raise HTTPException(status_code=400 ,detail=f"Water level [{latest_reading_level}] out of range (2-{Settings.MAX_WATER_LEVEL_VALIDATION})")
    
    filling_level_difference = round(latest_reading_level - last_reading.water_level, ndigits=1)
    draining_level_difference = round(last_reading.water_level - latest_reading_level,ndigits=1)
    
    logging.info(f'filling level difference after first validation: {filling_level_difference}')
    
# Filling tank validation
    if filling_level_difference > 0:
        logging.info('Filling mode detected')
        if last_reading.mode == 'FIRST':
            mode= 'NaN'
        elif last_reading.mode == 'DRAINING':
            mode= 'ADJUSTING'
            logging.info('Switching to ADJUSTING mode')
        else:
            mode= 'FILLING'
        

        if filling_level_difference < Settings.MIN_ALLOWED_FILLING_DIFFERENCE:
            DRAINING_RETRY_COUNT_DEFAULT = 0
            FILLING_RETRY_COUNT_DEFAULT = 0
            raise HTTPException(status_code=400, detail=f"Filling difference too small to validate ({filling_level_difference}) i.e < minimum allowed difference: {Settings.MIN_ALLOWED_FILLING_DIFFERENCE}")

        
        if filling_level_difference > Settings.MAX_ALLOWED_FILLING_DIFFERENCE:
            
            if FILLING_RETRY_COUNT_DEFAULT < Settings.MAX_RETRY_COUNT:
                print(f'-------{FILLING_RETRY_COUNT_DEFAULT}----------')
                FILLING_RETRY_COUNT_DEFAULT += 1
                print(f'-------{FILLING_RETRY_COUNT_DEFAULT}----------')
                raise HTTPException(status_code=400, detail=f"Steep filling detected: ({filling_level_difference}), more than {Settings.MAX_ALLOWED_FILLING_DIFFERENCE}, retry count: {FILLING_RETRY_COUNT_DEFAULT}/{Settings.MAX_RETRY_COUNT}, RETRYING...")
            else:
                logging.warning(f"Max retry count exceeded, validation passed : {last_reading.water_level} - {latest_reading_level} > {Settings.MIN_ALLOWED_FILLING_DIFFERENCE}")
                flag= 'RED'
                FILLING_RETRY_COUNT_DEFAULT = 0

        

#Draining tank validation
    else:
        logging.info('Tank in draining mode')
        mode= 'DRAINING'
       
        if last_reading.water_level - latest_reading_level < Settings.MIN_ALLOWED_DRAINING_DIFFERENCE:
            DRAINING_RETRY_COUNT_DEFAULT = 0
            FILLING_RETRY_COUNT_DEFAULT = 0
            raise HTTPException(status_code=400, detail=f"Draining difference too small to validate ({draining_level_difference}) i.e < minimum allowed difference: {Settings.MIN_ALLOWED_DRAINING_DIFFERENCE}")

        
        if draining_level_difference > Settings.MAX_ALLOWED_DRAINING_DIFFERENCE:
            
            if DRAINING_RETRY_COUNT_DEFAULT < Settings.MAX_RETRY_COUNT:
                print(f'-------{DRAINING_RETRY_COUNT_DEFAULT}----------')
                DRAINING_RETRY_COUNT_DEFAULT += 1
                print(f'-------{DRAINING_RETRY_COUNT_DEFAULT}----------')
                raise HTTPException(status_code=400, detail=f"Draining too fast ({draining_level_difference}), more than {Settings.MAX_ALLOWED_DRAINING_DIFFERENCE}, retry count: {DRAINING_RETRY_COUNT_DEFAULT}/{Settings.MAX_RETRY_COUNT}, RETRYING...")
            else:
                logging.warning(f"Max retry count exceeded, validation passed : {latest_reading_level} - {last_reading.water_level} > {Settings.MIN_ALLOWED_DRAINING_DIFFERENCE}")
                flag= 'RED'
                DRAINING_RETRY_COUNT_DEFAULT = 0
        
        

        if last_reading.mode == 'FILLING':
            logging.info('Tank was filling before this reading')
            read_filling=past_filling_read()
            if read_filling == 'NaN':
                past_fillings= 'NaN'
            else:
                past_fillings= f"{read_filling[5]} cm added in ({read_filling[2]}) at {read_filling[-1]} cm/min"
    
    DRAINING_RETRY_COUNT_DEFAULT = 0
    FILLING_RETRY_COUNT_DEFAULT = 0
    SENSOR_DISCREPANCY_DEFAULT = 0
    
    if last_reading.mode == 'FIRST':
        change= 'NaN'
    else:
        change= filling_level_difference

    
    logging.info(f"Validation passed successfully")
    return mode,change,past_fillings,flag
    


