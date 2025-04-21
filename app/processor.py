from fastapi import HTTPException
from app.csv_handler import latest_reading_read
from app.data_analysis import past_filling_read
from app.config import Settings, FILLING_RETRY_COUNT_DEFAULT, DRAINING_RETRY_COUNT_DEFAULT
import logging
from datetime import datetime, timezone


def calculator(reading,mean_sensor_duration):
    
    water_depth = round ((mean_sensor_duration * 0.0343) / 2, ndigits=1)

    water_level = round (Settings.TANK_HEIGHT - water_depth, ndigits=1)
    
    water_percentage = round ((water_level / Settings.MAX_WATER_LEVEL_CUTOFF) * 100, ndigits=1)
    
    water_volume = round ((3.14 * (Settings.TANK_RADIUS ** 2) * water_level) / 1000, ndigits=1)
    
    timestamp = datetime.fromtimestamp (reading.sensor_time).strftime("%Y-%m-%d %H:%M:%S")
    
    return [timestamp, water_level, water_percentage, water_volume]



def input_validation(sensor_duration):
    logging.info('Starting input validation')
    last_reading = latest_reading_read()
    latest_reading_level = round (Settings.TANK_HEIGHT - ((sensor_duration *0.0343)/2), ndigits=1)
    logging.info(f'Incoming level: {latest_reading_level}')
   
    #-------------------------
    global FILLING_RETRY_COUNT_DEFAULT # Imported global variable to keep track of retry count
    global DRAINING_RETRY_COUNT_DEFAULT # Imported global variable to keep track of retry count
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
        else:
            mode= 'FILLING'
        

        if filling_level_difference < Settings.MIN_ALLOWED_FILLING_DIFFERENCE:
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
            past_fillings= f"{read_filling[5]} cm added in ({read_filling[2]}) at {read_filling[-1]} cm/min"
    
    DRAINING_RETRY_COUNT_DEFAULT = 0
    FILLING_RETRY_COUNT_DEFAULT = 0
    if last_reading.mode == 'FIRST':
        change= 'NaN'
    else:
        change= filling_level_difference

    logging.info(f"Validation passed successfully")
    return mode,change,past_fillings,flag
    


