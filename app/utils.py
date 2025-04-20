




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