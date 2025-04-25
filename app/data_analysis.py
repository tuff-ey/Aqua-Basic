import logging
import os
from fastapi import HTTPException
import pandas as pd
from app.config import Settings
from app.csv_handler import recent_fillings_write, weekly_analysis
from app.utils import filling_time_format, average_volume, draining_rate, frequency
from pytz import timezone
IST = timezone('Asia/Kolkata')

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


#-----------------Past 7 days analysis--------------------
def past_week():
    try:
        file_path = os.path.join(os.getcwd(), "data", "data.csv")
        file=pd.read_csv(file_path).dropna(how='all')
        file['Timestamp'] = pd.to_datetime(file['Timestamp']).dt.tz_localize(IST)
        
        # Defining the time frame
        past_week= pd.to_datetime('now', utc=True).astimezone(IST).normalize() - pd.Timedelta(days=7)
        file=file[ file['Timestamp'] > past_week]
                
        # Filters for darinage and refill
        rows_adjusting_draining= ((file['Mode']=='ADJUSTING') & (file['Mode'].shift(-1) == 'DRAINING'))
        rows_draining_adjusting= ((file['Mode']=='DRAINING') & (file['Mode'].shift(1) == 'ADJUSTING'))
        rows_filling= (file['Mode']=='FILLING')
        rows_adjusting_filling= ((file['Mode']=='ADJUSTING') & (file['Mode'].shift(-1) == 'FILLING'))
        rows_draining_adjusting_filling= ((file['Mode']=='DRAINING') & (file['Mode'].shift(-1) == 'ADJUSTING') & (file['Mode'].shift(1) == 'FILLING'))

        # Filtered dataframes
        df_draining=file[~(rows_draining_adjusting | rows_adjusting_draining | rows_filling | rows_adjusting_filling | rows_draining_adjusting_filling)].set_index('Timestamp')
        df_filling=file[ rows_filling | rows_adjusting_filling ].set_index('Timestamp')
        
        active_hours= (df_draining.index.hour >= 8) & (df_draining.index.hour < 22)
        df_active_hours= df_draining[active_hours].copy()
       
        df_average_draining_volume=df_draining.resample('D').agg({'Change' : average_volume})
        df_draining_rate=df_active_hours.resample('D').agg({'Change' : draining_rate})
        df_average_filling_volume=df_filling.resample('D').agg({'Change' : average_volume})
        df_total_frequency_draining=df_draining.resample('D').agg({'Change' : frequency})
       
        combined_df= pd.concat([
            df_average_draining_volume.rename(columns={'Change': 'Avg Drain Volume'}),
            df_draining_rate.rename(columns={'Change': 'Drain Rate'}),
            df_average_filling_volume.rename(columns={'Change': 'Avg Fill Volume'}),
            df_total_frequency_draining.rename(columns={'Change': 'Drain Frequency'})
        ], axis=1)
       
        weekly_analysis(combined_df)
       
        return True
    
    except Exception as e:
        logging.error(f"Error in past week calculation: {e}")
        raise HTTPException(status_code=500, detail="Error in past week calculation")

