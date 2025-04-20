import logging
import os
import pandas as pd
from app.config import Settings
from app.csv_handler import past_fillings_write
from app.utils import filling_time_format

#-------------Past Fillings Analysis-----------------
def past_filling_read():
    
    try: 
        file_path = os.path.join(os.getcwd(), "data", "data.csv")
        file=pd.read_csv(file_path).dropna(how='all')
        logging.info("Past Filling CSV read successfully")
        
        if file.empty:
            logging.info("Past filling read failed: File is empty")
            
        file['Timestamp'] = pd.to_datetime(file['Timestamp'], format='%Y-%m-%d %H:%M:%S')
        mode=file['Mode'].astype('category')
        time=file['Timestamp']
        
        mode_fillings = mode.isin(['FILLING']) & (mode.shift(1).isin(['FILLING']) | mode.shift(-1).isin(['FILLING']))
        mode_noise= mode.isin(['DRAINING']) & (mode.shift(1).isin(['FILLING']) & mode.shift(-1).isin(['FILLING']))
        mode_time=((time.iloc[-1] - time) < pd.Timedelta(Settings.MAX_TIME_TO_FILL))
        

        fillings= file[mode_time & (mode_fillings | mode_noise)].copy()
        if fillings.empty:
            logging.info("Past filling read failed: No valid filling entries found")
            
        fillings['Filling Session']=(fillings['Timestamp'].diff() > pd.Timedelta(Settings.MAX_TIME_BETWEEN_TWO_FILLING_SESSIONS)).cumsum()
        
        session_list= list(fillings['Filling Session'].unique())
        if len(session_list) == 0:
            logging.info("Past filling read failed: No filling sessions found")
        
        last_session= fillings[fillings['Filling Session'] == session_list[-1]] 
        last_session_fillings= last_session[last_session['Mode'].isin(['FILLING'])]
        if len(last_session_fillings) < 2:
            logging.info("Past filling read failed: Not enough data points in the last session")
        
                
        session_start_time= last_session_fillings['Timestamp'].min()
        session_end_time= last_session_fillings['Timestamp'].max()
        duration= round(((session_end_time - session_start_time).total_seconds() / 60), ndigits=1) # raw output, needs to be formatted next
        session_duration= filling_time_format(duration) # in minutes and seconds
        session_start_level= last_session_fillings['Water Level'].min()
        session_end_level= last_session_fillings['Water Level'].max()
        water_level_added= round(session_end_level - session_start_level, ndigits=1) # in cm
        volume_added= round(last_session_fillings['Water Volume'].max() - last_session_fillings['Water Volume'].min(), ndigits=1) # in liters
        rate_of_fill= round((water_level_added / duration if duration > 0 else 0), ndigits=1) # in cm/min
        logging.info("Session data calculated, ready to return")

        filling_values = [session_start_time, session_end_time, session_duration, session_start_level, session_end_level, water_level_added, volume_added, rate_of_fill]
        past_fillings_write(filling_values)

        return filling_values
    
    except:
        logging.error("Returning past filling record as 'NaN' as Error in past filling read")
        return ['NaN']*8 # Return NaN values if any error occurs
    
#-----------------------Past 72 hours analysis---------------------------
def past_72_hours_analysis():
    pass