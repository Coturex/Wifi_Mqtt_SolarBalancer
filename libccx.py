#!/usr/bin/python3

import time, datetime, os, psutil
import configparser

config = configparser.ConfigParser()
config.read('config.ini') 

def now_ts():
    return time.time()
    
def checkProcessRunning(processName):
    # Checking if there is any running process that contains the given name processName.
    #Iterate over the all the running process
    for proc in psutil.process_iter():
        try:
            # Check if process name contains the given name string.
            if processName.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False;

def get_season():
    # get the current Day Of the Year
    doy = datetime.date.today().timetuple().tm_yday
    # "day of year" ranges for the northern hemisphere
    spring = range(80, 172)
    summer = range(173, 264)
    fall = range(265, 355)
    # winter = everything else

    if doy in spring:
        return 'spring'
    elif doy in summer:
        return 'summer'
    elif doy in fall:
        return 'fall'
    else:
        return 'winter'

def get_config(section, field, type = 'string', mandatory = False):
    """ Return config value"""
    global config
    types = ('bool','int','string')
    unset_words = ("none", "None", "NONE", "false", "False", "FALSE", "nok", "NOK")
    set_words = ("true", "True", "TRUE", "ok", "OK", )
    try:
        val = config[section][field]
    except Exception as e :
        if mandatory:
            return -404
        else:
            return 'None'

    if type == 'bool':
        if val in set_words:
            val = True
        elif val in unset_words:
            val = False
        else:
            val = None
    else:
        if val in unset_words:
            val = None
    return val


def main():
    import configparser

    print(get_config('xxx','xxstring'))
   
if __name__ == '__main__':
    main()
