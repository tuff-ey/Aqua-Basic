import logging
import os
import pandas as pd
from fastapi import HTTPException
from app.config import Settings



# Decimal time to HH:MM:SS format


def filling_time_format(t):
    if t>=0:
        if not t>=60:
            s=t-int(t)
            if s >= 0.992 and s<1:    
                min=int(t)+1
                sec=0
                return f'{min} mins {sec} seconds'
            else:
                sec=round(s*60)
                min=int(t)
                return f'{min} mins {sec} seconds'
        else:
            new_t= round(t)/60
            m=new_t-int(new_t)
            if m >= 0.992 and m<1:    
                hour=int(new_t)+1
                min=0
                if hour>1:
                    return f'{hour} hours {min} minutes'
                else:
                    return f'{hour} hour {min} minutes'
            else:
                min=round(m*60)
                hour=int(new_t)
                if hour>1:
                    return f'{hour} hours {min} minutes'
                else:
                    return f'{hour} hour {min} minutes'
                        
    else:
        return '0 mins 0 seconds'
    

# Average volume
def average_volume(series):
    total_change= abs(series.sum())
    return round ((3.14 * (Settings.TANK_RADIUS ** 2) * total_change) / 1000, ndigits=1)

# Rate of drainage
def draining_rate(series):
    total_change=abs(series.sum())
    total_time= (series.index.max() - series.index.min()).total_seconds()/3600 # in hours
    return round(total_change/max(total_time,0.01), ndigits=2)

# Frequency
def frequency(series):
    return series.count()

def backup_time(water_level):
    try:
        file_path = os.path.join(os.getcwd(), "data", "weekly_report.csv")
        file=pd.read_csv(file_path)
        average_drain_rate =round(file['Drain Rate'].mean(), ndigits=2)
        backup_time = round(((water_level - 7) / average_drain_rate), ndigits=1) *60 # in minutes
        final_time= filling_time_format(backup_time) # in minutes and seconds
        return final_time
    
    except Exception as e:
        logging.error(f"Error in backup time calculation: {e}")
        return 'NaN'
