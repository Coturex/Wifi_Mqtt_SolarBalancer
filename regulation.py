#!/usr/bin/python3
#!/usr/bin/env python

# Copyright (C) 2018-2019 Pierre Hebert
#                 Mods -> Coturex - F5RQG

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# WARNING: this software is exactly the one in use in the photovoltaic optimization project. It's tailored for my
#          own use and requires minor adaptations and configuration to run in other contexts.

# This is the main power regulation loop. It's purpose is to match the power consumption with the photovoltaic power.
# Using power measurements and a list of electrical equipments, with varying behaviors and control modes, the regulation
# loop takes decisions such as allocating more power to a given equipment when there is photovoltaic power in excess, or
# shutting down loads when the overall power consumption is higher than the current PV power supply.

# Beside the regulation loop, this software also handles these features
# - manual control ("force"), in order to be able to 'manually' turn on/off a given equipment with a specified power and
#   duration. (can be bind with Domotics device topic)
# - monitoring: sends a JSON status message on a MQTT topic for reporting on the current regulation state
# - fallback: a very specific feature which aim is to make sure that the water heater receives enough water (either
#   from the PV panels or the grid to keep the water warm enough.

# See the "equipment module" for the definitions of the loads.

import signal, sys, os, psutil, datetime, json, time
import paho.mqtt.client as mqtt

from debug_log import log as log
from debug_log import debug as debug

import cloud_prediction
from cloud_prediction import TOMORROW, Prediction

import equipment
from equipment import ConstantPowerEquipment, VariablePowerEquipment

import configparser
config = configparser.ConfigParser()
config.read('config.ini')

unset_words = ("none", "None", "NONE", "false", "False", "FALSE", "nok", "NOK")
set_words = ("true", "True", "TRUE", "ok", "OK", )

SIMULATION = False  
SIM_PROD = None
SIM_FALLBACK = False

# A debug switch to toggle simulation (uses distinct MQTT topics for instance)
if (config['debug']['simulation'] in set_words):
        SIMULATION = True
        print("**** SIMULATION IS SET")
        if (config['debug']['simul_prod'] in unset_words):
            SIM_PROD = None
            print("     PRODCUTION IS AS READ ON MQTT TOPIC")
        else:
            SIM_PROD = int(config['debug']['simul_prod'])
            print("     PROD IS SIMULATED AT " + str(SIM_PROD))
        
        if (config['debug']['simul_fallback'] in unset_words):
            SIM_FALLBACK = None
            print("     FALLBACK IS NOT SIMULATED")
        else:
            SIM_FALLBACK = True
            print("     FALLBACK IS SIMULATED ")
        #input("Enter to continue")
        time.sleep(2)

if (config['debug']['regulation_stdout'] in set_words): 
    SDEBUG = True 
else: SDEBUG = False

last_grid = None
last_injection = None
last_evaluation_date = None
last_production_date = None
last_consumption_date = None
last_grid_date = 0
last_injection_date = 0
last_zero_grid_date = 0
last_zero_injection_date = 0
last_saveStatus_date = None

fallback_today = False
init_today = False
cloud_requested = False
power_production = None
power_consumption = None
status = None
equipments = ()
equipment_water_heater = None

ECS_energy_yesterday = 0
ECS_energy_today = 0
production_energy = 0
CLOUD_forecast = None  
ECS_MODE = 20     # set to Domoticz value 20 wich is SOLAIRE_FEEDBACK widget level

PZEM_TIMEOUT = 30
weather = Prediction(config['cloudForecast']['location'],config['cloudForecast']['key'])

###############################################################
# MQTT CONFIG
mqtt_client = None
prefix = 'simu/' if SIMULATION else ''
MQTT_BROKER = config['mqtt']['broker_ip'] 
PORT = int(config['mqtt']['port'])
TOPIC_SENSOR_CONSUMPTION =  config['mqtt']['topic_cons'] 
TOPIC_SENSOR_PRODUCTION = config['mqtt']['topic_prod'] 
TOPIC_REGULATION = prefix + config['mqtt']['topic_regul'] 
TOPIC_FORCE = prefix + config['mqtt']['topic_force'] # forced/unforced duration - Can be bind to domotics device topic 
TOPIC_STATUS = prefix + config['mqtt']['topic_status']
TOPIC_ECSMODE = config['mqtt']['topic_ecsMode']
print (TOPIC_ECSMODE)

###############################################################
# DOMOTICZ CONFIG
TOPIC_DOMOTICZ_IN = prefix + "domoticz/in"
IDX_INJECTION = config['domoticz']['idx_injection']
IDX_GRID = config['domoticz']['idx_grid']
IDX_ECS_MODE = config['domoticz']['idx_ecs_mode']

if (config['domoticz']['send_domoticz'] in set_words): 
    SEND_DOMOTICZ = True 
else: SEND_DOMOTICZ = False
if (config['domoticz']['send_injection'] in set_words): 
    SEND_INJECTION = True 
else: SEND_INJECTION = False
if (config['domoticz']['send_grid'] in set_words): 
    SEND_GRID = True 
else: SEND_GRID = False

###############################################################
# EVELUATION CONFIG
# The comparison between power consumption and production is done every N seconds, it must be above the measurement
# rate, which is currently 2.5s with PZEM-004t v3.0  module.
EVALUATION_PERIOD = float(config['evaluate']['period'])
# Consider powers are balanced when the difference is below this value (watts). This helps prevent fluctuations.
BALANCE_THRESHOLD = int(config['evaluate']['balance_threshold'])
# Keep this margin (in watts) between the power production and consumption. This helps in reducing grid consumption
# knowing that there may be measurement inaccuracy.
MARGIN = int(config['evaluate']['margin'])
STATUS_TIME = int(config['evaluate']['status_time']) 
CHECK_AT = int(config['evaluate']['check_at']) 
if (CHECK_AT == 0 or CHECK_AT >= 24):
    CHECK_AT = 0
    CHECK_AT_prev = 23
elif (CHECK_AT >= 1):
    CHECK_AT_prev = CHECK_AT - 1   
else:
    log(0, "CHECK AT '{}' is out of range".format(str(CHECK_AT)))
    exit(0) 

INIT_AT = int(config['evaluate']['init_at']) 
if (INIT_AT == 0 or INIT_AT >= 24):
    INIT_AT = 0
    INIT_AT_prev = 23
elif (INIT_AT >= 1):
    INIT_AT_prev = INIT_AT - 1   
else:
    log(0, "CHECK AT '{}' is out of range".format(str(INIT_AT)))
    exit(0) 

###############################################################
# FUNCTIONS
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

def now_ts():
    return time.time()

def get_equipment_by_name(name):
    for e in equipments:
        if e.name == name:
            return e
    return None

def on_connect(client, userdata, flags, rc):
    debug(0, "Connected to BROKER " + MQTT_BROKER )
    debug(1, "Subscribing " + TOPIC_SENSOR_CONSUMPTION)
    debug(1, "Subscribing " + TOPIC_SENSOR_PRODUCTION)
    debug(1, "Subscribing " + TOPIC_ECSMODE)
    #debug(1, "Subscribing " + TOPIC_REGULATION_MODE)
    client.subscribe(TOPIC_SENSOR_CONSUMPTION)
    client.subscribe(TOPIC_SENSOR_PRODUCTION)
    client.subscribe(TOPIC_ECSMODE)
    client.subscribe("smeter/pzem/ECS")
    if(TOPIC_FORCE not in unset_words):
        debug(1, "Subscribing " + TOPIC_FORCE)
    global equipments
    for e in equipments:
        if (e.topic_read_power != None):
            debug(1, "Subscribing " + str(e.topic_read_power))

def on_message(client, userdata, msg):
    # Receive power consumption and production values and triggers the evaluation. We also take into account manual
    # control messages in case we want to turn on/off a given equipment.
    global power_production, power_consumption, last_production_date, last_consumption_date, production_energy
    global PZEM_TIMEOUT, ECS_MODE

    print("[on message] topic : " + msg.topic) if SDEBUG else ''
    now = now_ts()
    try:
        ##########
        # TOPIC DETECTED IS : CONSUMTION
        if msg.topic == TOPIC_SENSOR_CONSUMPTION:
            print("[on message]         conso : " + str(power_consumption) + ", prod : " + str(power_production)) if SDEBUG else ''
            j = json.loads(msg.payload.decode())
            power_consumption = int(j['power'])
            evaluate()
            last_consumption_date = now
        ##########
        # TOPIC DETECTED IS : PRODUCTION
        elif msg.topic == TOPIC_SENSOR_PRODUCTION:
            print("[on message]         conso : " + str(power_consumption) + ", prod : " + str(power_production)) if SDEBUG else ''
            j = json.loads(msg.payload.decode())
            power_production = int(j['power'])
            if last_production_date is not None:
                delta = now - last_production_date
                if delta < PZEM_TIMEOUT:
                    production_energy += power_production * delta / 3600.0
            if SIMULATION and SIM_PROD is not None:
                power_production = SIM_PROD
            evaluate()
            last_production_date = now
        ##########
        # TOPIC DETECTED IS : ECS_MODE
        elif msg.topic == TOPIC_ECSMODE :
            j = json.loads(msg.payload.decode())
            ECS_MODE = int(j['svalue1'])
            print("[on message]         ********************************** ECS_MODE : " + str(ECS_MODE)) if SDEBUG else ''
        ##########
        # TOPIC DETECTED IS : FORCE
        elif msg.topic == TOPIC_FORCE: 
            print("[on message]         Forcing...") if SDEBUG else ''
            j = json.loads(msg.payload.decode())
            command = j['command']
            name = j['name']
            if command == 'force':
                e = get_equipment_by_name(name)
                if e:
                    power = j['power']
                    msg = 'forcing equipment {} to {}W'.format(name, power)
                    duration = j.get('duration')  # duration is optional with default value None
                    if duration:
                        msg += ' for '+str(duration)+' seconds'
                    else:
                        msg += ' without time limitation'
                    debug(0, '')
                    debug(0, msg)
                    e.force(power, duration)
                    evaluate()
            elif command == 'unforce':
                e = get_equipment_by_name(name)
                if e:
                    debug(0, '')
                    debug(0, 'not forcing equipment {} anymore'.format(name))
                    e.force(None)
                    evaluate()

        ##########
        # TOPIC DETECTED IS : unknown        
        else: # This is a topic_read_power msg. Which equipment is 'over loaded'  ?
            for e in equipments:
                print("    Equipment : " + e.name)      if SDEBUG else ''   
                print("        topic_read_power : '" + str(e.topic_read_power)+"'") if SDEBUG else ''   
                print("        is_overed : " + str(e.is_overed()))      if SDEBUG else ''   
                
                if (e.topic_read_power is not None) and (not e.is_overed()):
                    if (msg.topic == e.topic_read_power):
                        print("            "+ e.name + " check over") if SDEBUG else ''
                        j = json.loads(msg.payload.decode())
                        e.measured_power = int(j[e.json_read_power])
    except Exception as e:
        if 'PZEM_READ_ERROR' in j:
            print("************* [on message]         pzem error") if SDEBUG else ''
        else :
            log(1, "*** Error on line {}".format(sys.exc_info()[-1].tb_lineno))
            log(4, e)
            log(4, j)
            print("*** [on message]         error, message badly formated") if SDEBUG else ''
            print("*** Error on line {}".format(sys.exc_info()[-1].tb_lineno))  if SDEBUG else ''
            print(e) if SDEBUG else ''
            print(j) if SDEBUG else ''

def signal_handler(sig, frame):
    """ End of program handler, set equipments 0W and save status"""
    global equipments, status
    if status is not None:
        signal_name = '(unknown)'
        if sig == signal.SIGINT:
            signal_name = 'SIGINT'
        elif sig == signal.SIGTERM:
            signal_name = 'SIGTERM'
        elif sig == signal.SIGUSR1:
            signal_name = 'SIGUSR1'
        elif sig == signal.SIGHUP:
            signal_name = 'SIGHUP'
        elif sig == signal.SIGBUS:
            signal_name = 'SIGBUS'
        print ("!! Received end signal : " + signal_name)
        log(0, "[signal_handler] !! Received end signal : " + signal_name)
        for e in equipments:
            e.set_current_power(0) 
            log(2, e.name + " : set power to 0") 
        time.sleep(2)
        log(4, "[saveStatus] saving status")
        saveStatus() if (config['debug']['use_persistent'] in set_words) else ''
        log(0, "Bye")
        exit(0) 
    else:
        print("signal handler ignored")

def loadStatus():
    global status, ECS_energy_today, ECS_energy_yesterday, CLOUD_forecast, production_energy, equipments
    log(0, "[loadStatus] loading status")
    try:
        statusFile = open('status.ini')
        j = json.load(statusFile)
        CLOUD_forecast = j['CLOUD_forecast']
        if CLOUD_forecast == 'null':
            CLOUD_forecast = None

        ECS_energy_yesterday = int(j['ECS_energy_yesterday'])
        production_energy = int(j['production_energy'])
        log(2,"CLOUD_forecast : " + str(CLOUD_forecast))
        log(2,"ECS_energy_yesterday : " + str(ECS_energy_yesterday))
        log(2,"production_energy : " + str(production_energy))
        i =0
        for e in equipments:
            log(0, "loading " + e.name )
            for i in range(len(j['equipments'])):
                if (e.name == j['equipments'][i]['name']):
                    #log(4, " find ; " + j['equipments'][i]['name']) 
                    nrj = int(j['equipments'][i]['energy'])
                    log(4, "read energy : " + str(nrj)) 
                    e.set_energy(nrj) 
                    over = j['equipments'][i]['overed']
                    if (over):
                        log(4, "read overloaded : " + str(over))
                        e.set_over()
                    else:
                        e.unset_over()    
    
    except Exception as e:
        log(1, "*** Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        log(1, e)
        log(2, "cannot load status.ini")
  
def saveStatus():
    global status
    if status is not None:
        try:
            with open('status.ini', 'w') as statusFile:
               json.dump(status, statusFile, indent=4, sort_keys=True)
            statusFile.close()
        except Exception as e:
            log(1, "*** Error on line {}".format(sys.exc_info()[-1].tb_lineno))
            log(1, e)
            log(2, "cannot save status.ini")

def get_season():
    # get the current Day Of the Year
    doy = datetime.date.today().timetuple().tm_yday
    
    try:
        # "day of year" ranges for my solar usage cf https://miniwebtool.com/day-of-year-calendar/
        spring_day = int(config['season']['yday_spring'])
        summer_day = int(config['season']['yday_summer'])
        fall_day = int(config['season']['yday_fall'])
        winter_day = int(config['season']['yday_winter'])
        spring = range(spring_day, summer_day )
        summer = range(summer_day, fall_day )
        fall   = range(fall_day, winter_day )
        # winter = everything else     
    except Exception:  
        log(0, '[get_season] config season bad format :')
        log(4, '  the northern hemisphere ranges are used instead')       
        # "day of year" official ranges for the northern hemisphere 
        spring = range(80, 172) # spring ranges for the northern hemisphere
        summer = range(173, 264) # summer ranges for the northern hemisphere
        fall = range(265, 355) # fall ranges for the northern hemisphere
        # winter = everything else
    #print (spring)
    #print (summer)
    #print (fall)
    
    if doy in spring:
        return 'spring'
    elif doy in summer:
        return 'summer'
    elif doy in fall:
        return 'fall'
    else:
        return 'winter'

def request_ECS_mode():  # domoticz request : does ECS is Jour/Nuit, Solaire_fallback, OFF   ?
    # Request Device Info
    # {"command": "getdeviceinfo", "idx": 2450 }
    domoticz = "{ \"command\": \"getdeviceinfo\", \"idx\": " + IDX_ECS_MODE + "}"
    mqtt_client.publish(TOPIC_DOMOTICZ_IN, domoticz) 
    print(TOPIC_DOMOTICZ_IN, domoticz) if SDEBUG else ''

def send_keep_alive():  # domoticz request : does ECS is Jour/Nuit, Solaire_fallback, OFF   ?
    # Send keep Alive to Domoticz Device
    # {"command": "getdeviceinfo", "idx": 2450 }
    IDX_KEEP_ALIVE = "658"
    domoticz = "{ \"idx\": " + IDX_KEEP_ALIVE + ", \"nvalue\": 1}"
    mqtt_client.publish(TOPIC_DOMOTICZ_IN, domoticz)    
    debug(0, TOPIC_DOMOTICZ_IN + domoticz)
    #print("###################################################################" + TOPIC_DOMOTICZ_IN + domoticz)
    

def low_energy_fallback():
    """ Fallback, when the amount of energy today went below a minimum"""
    # This is a custom and very specific fallback method which aim is to turn on the water heater should the daily
    # solar energy income be below a minimum threshold. We want the water to stay warm.
    # The check is done everyday

    global ECS_energy_yesterday, ECS_energy_today, CLOUD_forecast, power_production, equipment_water_heater, ECS_MODE
  
    try:
        season = get_season()
        LOW_ECS_ENERGY_TODAY = int(config['fallback']['low_nrj_today_' + season]) # minimal power on two days
        LOW_ECS_ENERGY_TWO_DAYS = int(config['fallback']['low_nrj_two_days_' + season]) # minimal power for today
        FULL_ECS = int(config['ecs']['full']) # total energy in a full ECS
        MORNING_ECS = int(config['ecs']['morning']) # minimun of morning ecs energy needs (to assure first 'douche') 
        GOOD_FORECAST = int(config['evaluate']['good_forecast']) # good forecast level
        ecs_measure_correction =  float(config['evaluate']['ecs_measure_correction'])
        log(0, '[low_energy_fallback] Season "{}" : '.format(season))
        log(2, "need ENERGY_TODAY : " + str(LOW_ECS_ENERGY_TODAY))
        log(2, "need ENERGY_TWO_DAYS : " + str(LOW_ECS_ENERGY_TWO_DAYS))
        log(2, "need MORNING_ECS : " + str(MORNING_ECS))
    
    except Exception as e:
        log(0,"[low_energy_fallback]") 
        log(1, "*** Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        log(1, e)
        log(2, "then set to default 7000 / 12000")
        LOW_ECS_ENERGY_TODAY = 7000
        LOW_ECS_ENERGY_TWO_DAYS = 12000
        ecs_measure_correction = 1
            
    max_power = int(equipment_water_heater.MAX_POWER)
    duration_correction = 1.07   # this duration_correction depend on ECS heater resistor, mine is not stable at max of power and the average power go down
    two_days_nrj = int(ECS_energy_today + ECS_energy_yesterday)
    ECS_energy_today = int(ECS_energy_today * ecs_measure_correction)
    left_energy = 0
    log(2, "--")
    log(2, "Cloud forecast : " + str(CLOUD_forecast))
    log(2, 'ECS Energy Today : {}'.format(str(int(ECS_energy_today))))
    log(2, 'ECS Energy Yesterday : {}'.format(str(int(ECS_energy_yesterday))))
    log(2, 'ECS Energy Two days : {}'.format(str(int(two_days_nrj))))
    request_ECS_mode()
    time.sleep(5)
    log(2, "ECS_MODE : " + str(ECS_MODE))

    if (config['cloudForecast'][season] in unset_words):
        CLOUD_forecast = 100
        log(2, str(season) + " cloud forecast forced to bad: " + str(CLOUD_forecast))

    if (ECS_MODE < 20):
        log(4, '0- ECS MODE IS NOT SET TO SOLAIRE_Feedback here json svalue1 = 0 (OFF) or 10 (JOUR/NUIT) ')
        log(8, 'CANCELLING fallback')
    elif(equipment_water_heater.is_overed()):
        log(4, '1- ECS Energy has been OVERLOADED TODAY')
        log(8, 'CANCELLING fallback')
        ECS_energy_today = FULL_ECS

    elif (ECS_energy_today) < LOW_ECS_ENERGY_TODAY:
    # HERE ECS Energy today < LOW_ECS_ENERGY_TODAY

        left_today = int(LOW_ECS_ENERGY_TODAY - ECS_energy_today)
        log(4, "left today : " + str(left_today))

        if two_days_nrj < LOW_ECS_ENERGY_TWO_DAYS:
            left_two_days = int(LOW_ECS_ENERGY_TWO_DAYS - two_days_nrj)
            log(4, "left two days : " + str(left_two_days))
            
        # Here two_days_nrj < LOW_ECS_ENERGY_TWO_DAYS
            if CLOUD_forecast < GOOD_FORECAST:  
            # Here Good forecast but no more 3-4 kw is needed !
                left_energy = int(min(left_today, left_two_days))
                if (left_energy > MORNING_ECS):
                    left_energy = MORNING_ECS
                duration = 3600 * left_energy / max_power
                log(4, '2- cloud forecast is good ({} %) but not enough today ({} W) and 2 days energy ({} W)'.format(CLOUD_forecast, ECS_energy_today, two_days_nrj))
                log(8, 'completing today OR two days energy and no more 3-4kW, adding {} W'.format(left_energy))
                log(8, 'forcing ECS {} to {} W for {} min'.format(equipment_water_heater.name, max_power, int(duration/60)))
                equipment_water_heater.force(max_power, duration * duration_correction)

            else:  
            # Here Bad forecast, at least 3-4kw + x is needed
                # left_energy = int(MORNING_ECS + (left_today - MORNING_ECS) * (CLOUD_forecast / 100))
                # 4kw + x calculation
                log(4, '3- cloud forecast not good ({} %) and not enough 2 days energy ({} W)'.format(CLOUD_forecast, two_days_nrj))
                if (ECS_energy_today < MORNING_ECS):
                    left_energy = int((MORNING_ECS - ECS_energy_today) + ((LOW_ECS_ENERGY_TODAY - MORNING_ECS) * CLOUD_forecast / 100))
                    log(8, '3.1- completing % TODAY energy, adding {} W ({}-{}+({}-{})*{}/100)'.format(left_energy,MORNING_ECS,ECS_energy_today,LOW_ECS_ENERGY_TODAY,MORNING_ECS,CLOUD_forecast))
                else:
                    #left_energy = int(left_today * (CLOUD_forecast / 100))
                    left_energy = int((LOW_ECS_ENERGY_TODAY - ECS_energy_today) * CLOUD_forecast / 100)
                    log(8, '3.2- completing % TODAY energy, adding {} W (({}-{})*{}/100)'.format(left_energy,LOW_ECS_ENERGY_TODAY,ECS_energy_today,CLOUD_forecast))
                duration = 3600 * left_energy / max_power
                log(8, 'forcing ECS  {} to {} W for {} min'.format(equipment_water_heater.name, max_power, int(duration/60)))
                equipment_water_heater.force(max_power, duration * duration_correction)            
 
        # Here two_days_nrj > LOW_ECS_ENERGY_TWO_DAYS
        else:   
            if CLOUD_forecast < GOOD_FORECAST:  
            # Here Good forecast
                log(4, '4- cloud forecast is good ({} %) and enough 2 days energy ({} W)'.format(CLOUD_forecast, two_days_nrj))
                log(8, 'even there is not enough energy stored  today ({} W)'.format(ECS_energy_today))
                log(8, 'CANCELLING fallback')

            else:   
            # Here Bad forecast
                if season == 'winter':  
                # Here Season IS WINTER 
                    left_energy = left_today
                    duration = 3600 * left_energy / max_power
                    log(4, '5- cloud forecast not good ({} %) 2 days energy enough ({} W) BUT season is {})'.format(CLOUD_forecast, two_days_nrj, season))
                    log(8, 'completing TODAY energy, adding {} W'.format(left_energy))
                    log(8, 'forcing ECS {} to {} W for {} min'.format(equipment_water_heater.name, max_power, int(duration/60)))
                    equipment_water_heater.force(max_power, duration * duration_correction)
                else:
                # Here Season SUMMER
                    if season == 'summer': 
                        log(4, '7- cloud forecast not good ({} %) 2 days energy enough ({} W) AND season is {}'.format(CLOUD_forecast, two_days_nrj, season))
                        log(8, 'NOTHING TO COMPLETE')
                    else:
                    # Here Season IS SPRING, FALL
                        left_energy = left_today * (CLOUD_forecast / 100)
                        duration = 3600 * left_energy / max_power
                        log(4, '6- cloud forecast not good ({} %) 2 days energy enough ({} W) BUT season is {})'.format(CLOUD_forecast, two_days_nrj, season))
                        log(8, 'completing % TODAY energy, adding {} W ({}*{}/100)'.format(left_energy,left_today,CLOUD_forecast))
                        log(8, 'forcing ECS {} to {} W for {} min'.format(equipment_water_heater.name, max_power, int(duration/60)))
                        equipment_water_heater.force(max_power, duration * duration_correction)              
    else: 
    # HERE ECS Energy today > LOW_ECS_ENERGY_TODAY
        log(4, '8- ECS Energy today {} W is enouth, no need to complete it.'.format(ECS_energy_today))
        log(8, 'CANCELLING fallback')

    # save the energy so that it can be used in the fallback check tomorrow
    ECS_energy_yesterday = ECS_energy_today + left_energy
        
def evaluate():
    # This is where all the magic happen. This function takes decision according to the current power measurements.
    # It examines the list of equipments by priority order, their current state and computes which one should be
    # turned on/off.

    global last_evaluation_date, ECS_energy_today, last_injection, last_grid, CLOUD_forecast
    global equipments, equipment_water_heater, production_energy, fallback_today, init_today, cloud_requested, status
    global power_production, power_consumption, last_production_date, last_consumption_date, status
    global last_grid_date, last_injection_date,last_zero_grid_date, last_zero_injection_date
    global SIM_FALLBACK, INIT_AT, INIT_AT_prev, CHECK_AT, CHECK_AT_prev, last_saveStatus_date, STATUS_TIME
    TODAY = 0 
    TOMORROW = 1

    try:
        t = now_ts()
        
        ##########
        # SCHEDULER
        if last_evaluation_date is not None: # Evaluating scheduler
            
            # ensure there's a minimum duration between two evaluations
            if t - last_evaluation_date < EVALUATION_PERIOD:
                return

            d1 = datetime.datetime.fromtimestamp(last_evaluation_date)
            d2 = datetime.datetime.fromtimestamp(t)

            if d1.minute == 20 and d2.minute == 21:  # every hours and 3 minutes (...14h03, 15h03...)
                #print ("**************************************************************************")
                send_keep_alive()  
               
            if d1.hour == INIT_AT_prev and d2.hour == INIT_AT and not init_today: # ensure it's not already done for today
                log(0,"[evaluate] ECS energy / Over : " + str(equipment_water_heater.get_energy()) + " / " + str(equipment_water_heater.is_overed()))
                equipment_water_heater.unset_over() # maybe it has been forced this night (low_energy_fallback)
                equipment_water_heater.reset_energy()
                log(0,"           ECS energy / Over : " + str(equipment_water_heater.get_energy()) + " / " + str(equipment_water_heater.is_overed()))
                fallback_today = False
                init_today = True
                return

            if SIM_FALLBACK and not fallback_today:
                fallback_today = True
                print("Simulating low_energy_fallback...")
                low_energy_fallback()

            if d1.hour == CHECK_AT_prev and d2.hour == CHECK_AT and not fallback_today:  # fallback_today : ensure it's not already done for today
            #if True and not fallback_today:  # fallback_today : be sure it's not already done for today
                fallback_today = True
                log(0,"------------------------------------------------------------")
                log(0,"[evaluate] Past Cloud / Production / Water_heater")
                log(8, "csv : {} ; {} ; {}".format(CLOUD_forecast, int(production_energy), ECS_energy_today) )
                CLOUD_forecast = -1
                retry = 0
                while CLOUD_forecast < 0 and retry < 5:
                    log(0,"[evaluate] Cloud request : " + str(retry))
                    retry = retry + 1
                    if (CHECK_AT > 7 and CHECK_AT < 24):
                        log(0,"[evaluate] Cloud Forecast Tomorrow : " + str(CLOUD_forecast))
                        CLOUD_forecast = weather.getCloudAvg(TOMORROW)
                    elif (CHECK_AT >= 0):
                        log(0,"[evaluate] Cloud Forecast Today : " + str(CLOUD_forecast))
                        CLOUD_forecast = weather.getCloudAvg(TODAY)
                    time.sleep(5) # Delays for 5 seconds
                log(0,"[evaluate] Cloud forcast : " + str(CLOUD_forecast))
                if (CLOUD_forecast == -404):
                    log(0,"*** cannot contact weather server")
                    log(4,"FORCING CLOUD Forecast to 100 %")  
                    CLOUD_forecast = 100 
                elif (CLOUD_forecast == -1):
                    log(0,"*** cloudForecast is out of range")
                    log(4,"FORCING CLOUD Forecast to 100 %")   
                    CLOUD_forecast = 100 

                ECS_energy_today = equipment_water_heater.get_energy()
                equipment_water_heater.reset_energy()
                production_energy = 0
                # ensure that water stays warm enough
                low_energy_fallback()
                init_today = False
                return

        ##########
        last_evaluation_date = t
        if power_production is None or power_consumption is None: # Return if None
            return
        if last_consumption_date is None or last_production_date is None:
            return  

        debug(0, '')
        debug(0, '[evaluate] evaluating power CONS = {}, PROD = {}'.format(power_consumption, power_production))
        debug(0, '[evaluate] ECS Energy today {}'.format(equipment_water_heater.get_energy()))

        ##########
        # IS PZEM TIMEOUT ?
        if (t - last_consumption_date) > PZEM_TIMEOUT or (t- last_production_date) > PZEM_TIMEOUT:
                power_consumption = 0
                power_production = 0
                delta_cons = int(t - last_consumption_date)
                delta_prod = int(t - last_production_date )
                log(0, "*** MQTT RX : PZEM CONSUMPTION ({}s) OR PRODUCTION ({}s) TIMEOUT".format(delta_cons, delta_prod))
                log(4, "reset all power equipments to 0")
                for e in equipments:
                    if e.is_forced():
                        log(8, "skipping {} because it's forced".format(e.name))
                    else:
                        e.set_current_power(0)
        ##########
        # REAL WORK
        else:
            # HERE STARTS THE REAL WORK, compare powers

            # Check which equipment is over
            for e in reversed(equipments):
                if e.measured_power is not None:
                    e.check_over()

            # if, TOO CONSUMPTION, POWER IS NEEDED, decrease the load
            if power_consumption > (power_production - MARGIN): 
                excess_power = power_consumption - (power_production - MARGIN)
                debug(0, "[evaluate] decreasing global power consumption by {}W".format(excess_power))
                for e in reversed(equipments):
                    debug(2, "1. examining " + e.name)
                    if e.is_overed():
                        debug(4, "skipping this equipment because it's already full loaded for today")
                        continue
                    if e.is_forced():
                        debug(4, "skipping this equipment because it's in forced state")
                        continue
                    result = e.decrease_power_by(excess_power)
                    if result is None:
                        debug(2, "stopping here and waiting for the next measurement to see the effect")
                        break
                    excess_power -= result
                    if excess_power <= 0:
                        debug(2, "[no more excess power consumption, stopping here")
                        break
                    else:
                        debug(2, "There is {}W left to cancel, continuing".format(excess_power))
                debug(2, "No more equipment to check")
            elif (power_production - MARGIN - power_consumption) < BALANCE_THRESHOLD: 
                # Nice, this is the goal: CONSUMPTION is EQUAL to PRODUCTION
                debug(0, "[evaluate] power consumption and production are balanced")
            else: # There's PV POWER IN EXCESS, try to increase the load to consume this available power
                available_power = power_production - MARGIN - power_consumption
                debug(0, "[evaluate] increasing global power consumption by {}W".format(available_power))
                for i, e in enumerate(equipments):                
                    if available_power <= 0:
                        debug(2, "no more available power")
                        break
                    debug(2, "2. examining " + e.name)

                    if e.is_overed():
                        debug(4, "skipping this equipment because it's already full loaded for today")
                        
                        continue
                    if e.is_forced():
                        debug(4, "skipping this equipment because it's in forced state")
                        
                        continue
                    result = e.increase_power_by(available_power)
                    if result is None:
                        debug(2, "stopping here and waiting for the next measurement to see the effect")
                        break
                    elif result == 0:
                        debug(2, "no more available power to use, stopping here")
                        break
                    elif result < 0:
                        debug(2, "not enough available power to turn on this equipment, trying to recover power on lower priority equipments")
         
                        freeable_power = 0
                        needed_power = -result
                        for j in range(i + 1, len(equipments)):
                            o = equipments[j]
                            if o.is_forced():
                                continue
                            p = o.get_current_power()
                            if p is not None:
                                freeable_power += p
                        debug(2, "power used by other equipments: {}W, needed: {}W".format(freeable_power, needed_power))
                        if freeable_power >= needed_power:
                            debug(2, "recovering power")
                            freed_power = 0
                            for j in reversed(range(i + 1, len(equipments))):
                                o = equipments[j]
                                if o.is_forced():
                                    continue
                                result = o.decrease_power_by(needed_power)
                                freed_power += result
                                needed_power -= result
                                if needed_power <= 0:
                                    debug(2, "enough power has been recovered, stopping here")
                                    break
                            new_available_power = available_power + freed_power
                            debug(2, "now trying again to increase power of {} with {}W".format(e.name, new_available_power))
                            available_power = e.increase_power_by(new_available_power)
                        else:
                            debug(2, "this is not possible to recover enough power on lower priority equipments")
                    else:
                        available_power = result
                        debug(2, "there is {}W left to use, continuing".format(available_power))
                debug(2, "no more equipment to check")
        
        ##########
        # DOMOTICZ COMMUNICATION
        if SEND_DOMOTICZ: # THEN SEND GRID & INJECTION MESSAGE
            injection = (power_consumption - power_production) 
            if injection < 0:   # This is INJECTION
                grid = 0
                last_injection_date = t
            else:               # This is GRID
                grid = injection
                injection = 0
                last_grid_date = t
            #print ("***** SIMULATION DOMOTICZ INJECTION GRID : {} {} {} {}".format(SIMULATION, SEND_DOMOTICZ, SEND_INJECTION, SEND_GRID)) if SDEBUG else ''
            ### HERE Prepare and send  INJECTION MESSAGE
            if SEND_INJECTION:
                if injection < 0 and last_injection == 0 and (t - last_injection_date) > 20 : 
                    # This Workaround is needed in order to improve Grafana Integral calculation. Send 0.
                    domoticz = "{ \"idx\": " + IDX_INJECTION + ", \"nvalue\": 0, \"svalue\": \"0\"}"
                    mqtt_client.publish(TOPIC_DOMOTICZ_IN, domoticz) 
                    print(TOPIC_DOMOTICZ_IN, domoticz) if SDEBUG else ''
                if injection < 0:
                    domoticz = "{ \"idx\": " + IDX_INJECTION + ", \"nvalue\": 0, \"svalue\": \"" + str(injection) + "\"}"
                    mqtt_client.publish(TOPIC_DOMOTICZ_IN, domoticz) 
                    print(TOPIC_DOMOTICZ_IN, domoticz) if SDEBUG else ''
            
                if injection == 0 and last_injection == 0:
                    # Do not repeat this point 
                    pass
                elif injection == 0:
                    domoticz = "{ \"idx\": " + IDX_INJECTION + ", \"nvalue\": 0, \"svalue\": \"0\"}"
                    mqtt_client.publish(TOPIC_DOMOTICZ_IN, domoticz) 
                    print(TOPIC_DOMOTICZ_IN, domoticz) if SDEBUG else ''
                    
            ### HERE Prepare and send  GRID MESSAGE
            if SEND_GRID:
                if grid > 0 and last_grid == 0 and (t - last_grid_date) > 20 : 
                    # This Workaround is needed to improve Grafana Integral calculation. Send 0.
                    domoticz = "{ \"idx\": " + IDX_GRID + ", \"nvalue\": 0, \"svalue\": \"0\"}"
                    mqtt_client.publish(TOPIC_DOMOTICZ_IN, domoticz)
                    print(TOPIC_DOMOTICZ_IN, domoticz) if SDEBUG else ''
                if grid > 0:
                    domoticz = "{ \"idx\": " + IDX_GRID + ", \"nvalue\": 0, \"svalue\": \"" + str(grid) + "\"}"
                    mqtt_client.publish(TOPIC_DOMOTICZ_IN, domoticz)
                    print(TOPIC_DOMOTICZ_IN, domoticz) if SDEBUG else ''

                if grid == 0 and last_grid == 0:
                    # Do not repeat this point if last zero grid is not older than 30min (this is a keepalive for Domoticz)
                    if (t - last_zero_grid_date > 1800 ):
                        domoticz = "{ \"idx\": " + IDX_GRID + ", \"nvalue\": 0, \"svalue\": \"0\"}"
                        mqtt_client.publish(TOPIC_DOMOTICZ_IN, domoticz)
                        print(TOPIC_DOMOTICZ_IN, domoticz) if SDEBUG else ''
                        last_zero_grid_date = t
                elif grid == 0:
                    domoticz = "{ \"idx\": " + IDX_GRID + ", \"nvalue\": 0, \"svalue\": \"0\"}"
                    mqtt_client.publish(TOPIC_DOMOTICZ_IN, domoticz)
                    print(TOPIC_DOMOTICZ_IN, domoticz) if SDEBUG else ''
                    last_zero_grid_date = t
            print("[evaluate]                    CALCULATED INJECTION :", injection) if SDEBUG else ''
            print("[evaluate]                    CALCULATED GRID      :", grid) if SDEBUG else ''        
            last_injection = injection
            last_grid = grid
  
        ##########
        # Build an MQTT status message, and status file
        status = None
        msg = {
            'date': int(t),
            'date_str': datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S'),
            'power_consumption': power_consumption,
            'power_production': power_production,
            'production_energy': round(production_energy),
            'injection' : injection,
            'grid' : grid,
            'CLOUD_forecast' : CLOUD_forecast,
            'ECS_energy_yesterday' : int(ECS_energy_yesterday),
        }
        power_equipments = 0
        eq = []
        for e in equipments:
            p = int(e.get_current_power())       
            power_equipments = power_equipments + p             
            eq.append({
                'name': e.name,
                'current_power': 'unknown' if p is None else p,
                'energy': e.get_energy(),
                'overed' : e.is_overed(),
                'forced': e.is_forced()
            })
        msg['power_equipments'] = power_equipments
        msg['power_house'] = power_consumption - power_equipments
        msg['equipments'] = eq
        status = msg
        mqtt_client.publish(TOPIC_STATUS, json.dumps(msg))
        if last_saveStatus_date is None:
            last_saveStatus_date = t
        else:
            if t - last_saveStatus_date > STATUS_TIME and STATUS_TIME >= 60:
                saveStatus()    
                last_saveStatus_date = t

    except Exception as e:
        log(0,"[evaluate exception]") 
        log(1, "*** Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        log(1, e)

###############################################################
# MAIN

def main():
    global mqtt_client, equipments, equipment_water_heater
    signal.signal(signal.SIGINT, signal_handler) 
    signal.signal(signal.SIGHUP, signal_handler) 
    signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGBUS, signal_handler)
    
    if os.uname()[1] == "raspberry":
        while checkProcessRunning("mosquitto") is False:
            time.sleep(5)

    debug(0,"")
    log(0,"")
    log(0,"[Main] Starting PV Power Regulation @" + config['cloudForecast']['location'])

    mqtt_client = mqtt.Client()
    equipment.setup(mqtt_client, SIMULATION, prefix)
   
    # Dynamic Load of equipments list
    # This list of EQUIPMENTS IS PRIORITY ORDERED (first one has the higher priority). 
    # As many equipments as needed can be listed in config.ini, [equiments] section.
    log(0, "Making list of equipments :")
    i = -1
    for eq_name in config['equipments']:
        i += 1
        type = config['equipments'][eq_name]
        if (i == 0 and type != "water_heater"):
            log(1, "The first equipment must be 'water_heater' type" + type)
            exit(0)
        if (i == 0 and type == "water_heater"):
            log(1, "Instancing [" + eq_name + "] as 'variable' equipment")
            equipment_water_heater = VariablePowerEquipment(eq_name)
            equipments += (equipment_water_heater,)  # append it to the end of list
            continue
        if ( type == "constant"):
            log(1, "Instancing [" + eq_name + "] as 'constant' equipment") 
            equipments += (ConstantPowerEquipment(eq_name),) # append it to the end of list
            continue
        if ( type == "variable"):
            log(1, "Instancing [" + eq_name + "] as 'variable' equipment") 
            equipments += (ConstantPowerEquipment(eq_name),) # append it to the end of list
            continue
        
    #equipment_water_heater = VariablePowerEquipment('ECS')
    
    log(0, "Equipments :")
    # At startup, reset everything - Mandatory !
    for eq in equipments:
        eq.set_current_power(0) 
        log(1, str(eq.name) + " power type : " + eq.type)
        log(1, str(eq.name) + " set power topic : " + str(eq.topic_set_power))
        log(1, str(eq.name) + " read power topic : " + str(eq.topic_read_power))
        log(1, str(eq.name) + " power min : " + str(eq.MIN_POWER) + " W" )
        log(1, str(eq.name) + " power max : " + str(eq.MAX_POWER) + " W" )
        if (eq.type == "variable"):
            log(1, str(eq.name) + " percent min : " + str(eq.MIN_PERCENT) + " %" )

    loadStatus() if (config['debug']['use_persistent'] in set_words) else ''
        
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    try:
        mqtt_client.connect(MQTT_BROKER, PORT , 120)
    except:
        print("Cannot connect " + MQTT_BROKER)
        sys.exit()
    mqtt_client.loop_forever()

if __name__ == '__main__':
    main()
