import logging
import os
from fastapi import HTTPException
import pandas as pd
from app.config import Settings
from app.csv_handler import recent_fillings_write
from app.utils import filling_time_format

#-------------Past Fillings Analysis-----------------
def recent_filling_calculation():
    
    try: 
        file_path = os.path.join(os.getcwd(), "data", "data.csv")
        file=pd.read_csv(file_path).dropna(how='all')
        logging.info("Past Filling CSV read successfully")
        
        if file.empty:
            logging.info("Past filling read failed: File is empty")
            return 'NaN'

        file['Timestamp'] = pd.to_datetime(file['Timestamp'], format='%Y-%m-%d %H:%M:%S')
        mode=file['Mode'].astype('category')
        time=file['Timestamp']
        
        mode_fillings = mode.isin(['FILLING']) & (mode.shift(-1).isin(['FILLING']) | mode.shift(1).isin(['FILLING','ADJUSTING']))
        mode_noise= mode.isin(['DRAINING']) & (mode.shift(-1).isin(['ADJUSTING']) & mode.shift(1).isin(['FILLING']))
        mode_adjusting = (mode.isin(['ADJUSTING'])) & (mode.shift(-1).isin(['FILLING']))
        mode_time=((time.iloc[-1] - time) < pd.Timedelta(Settings.MAX_TIME_TO_FILL))
        

        fillings= file[mode_time & (mode_fillings | mode_noise | mode_adjusting)].copy()
        
        if fillings.empty:
            logging.info("Past filling read failed: No valid filling entries found")
            return 'NaN'
            
        fillings['Filling Session']=(fillings['Timestamp'].diff() > pd.Timedelta(Settings.MAX_TIME_BETWEEN_TWO_FILLING_SESSIONS)).cumsum()
        
        session_list= list(fillings['Filling Session'].unique())
        
        if len(session_list) == 0:
            logging.info("Past filling read failed: No filling sessions found")
            return 'NaN'
        
        last_session= fillings[fillings['Filling Session'] == session_list[-1]] 
        last_session_fillings= last_session[last_session['Mode'].isin(['FILLING','ADJUSTING'])]
        
        if len(last_session_fillings) < 2:
            logging.info("Past filling read failed: Not enough data points in the last session")
            return 'NaN'
        
                
        session_start_time= last_session_fillings['Timestamp'].min()
        session_end_time= last_session_fillings['Timestamp'].max()
        duration= round(((session_end_time - session_start_time).total_seconds() / 60) + Settings.FILLING_DURATION_CALIBRATION_TIME, ndigits=1) # in mins
        session_duration= filling_time_format(duration) # in minutes and seconds
        session_start_level= last_session_fillings['Water Level'].min()
        session_end_level= last_session_fillings['Water Level'].max()
        water_level_added= round(session_end_level - session_start_level, ndigits=1) # in cm
        volume_added= round(last_session_fillings['Water Volume'].max() - last_session_fillings['Water Volume'].min(), ndigits=1) # in liters
        rate_of_fill= round((water_level_added / duration if duration > 0 else 0), ndigits=2) # in cm/min
        logging.info("Session data calculated, ready to return")

        filling_values = [session_start_time, session_end_time, session_duration, session_start_level, session_end_level, water_level_added, volume_added, rate_of_fill]
        recent_fillings_write(filling_values)

        return filling_values
    
    except:
        logging.error("Returning past filling record as 'NaN' as Error in past filling calculation")
        return 'NaN'
    
#-----------------------Leak detection---------------------------
def leak_check(past_reading_time, sensor_time, min_time=3, max_time=6, min_change=-1.6, max_change=-1):
    
    previous_timestamp = pd.to_datetime(past_reading_time)
    current_timestamp = pd.to_datetime(sensor_time)
    difference= (current_timestamp - previous_timestamp).total_seconds() / 60 # in minutes
    
    if min_time <= difference <= max_time:
        logging.info("Time difference is within the acceptable range for leak detection")
        try: 
            file_path = os.path.join(os.getcwd(), "data", "data.csv")
            file=pd.read_csv(file_path).dropna(how='all')
                    
            if file.empty:
                logging.info("Leak check failed: File is empty")
                raise HTTPException(status_code=404, detail="File is empty")

            file=file.tail(5)
            file['Timestamp']=pd.to_datetime(file['Timestamp'])
            file['Time Difference']= (file['Timestamp'].diff()).dt.total_seconds()/60 # in minutes
            file=file.tail(3)
            time_difference= file['Time Difference'].between(min_time,max_time).all()
            change= file['Change'].between(min_change,max_change).all()
            leak = time_difference & change
            logging.info(f"Leak check: leak = {leak}")
            if leak== True:
                logging.info("----->Leak detected<-----")
                return leak
            
            else:
                logging.info("No leak detected")
                return False

        except:
            logging.error("Leak check failed: Error in leak check calculation")
            raise HTTPException(status_code=500, detail="Error in leak check calculation")
    
    else:
        logging.info("Time difference is outside the acceptable range for leak detection")
        return False