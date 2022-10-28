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


import datetime
import json
from pickletools import string1
import time
import signal, sys
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

# A debug switch to toggle simulation (uses distinct MQTT topics for instance)
if (config['debug']['simulation'].lower() == "true"):
        SIMULATION = True
        print("**** SIMULATION IS SET")
        SIM_PROD = int(config['debug']['simul_prod'])
else:
        SIMULATION = False

if (config['debug']['regulation_stdout'].lower() == "true"): 
    SDEBUG = True 
else: SDEBUG = False

test = True
last_evaluation_date = None
last_injection = None
last_grid = None
power_production = None
power_consumption = None
last_power_production_date = None

equipments = None
equipment_water_heater = None

ECS_energy_yesterday = 0
ECS_energy_today = 0
production_energy = 0
CLOUD_forecast = None  

weather = Prediction(config['openweathermap']['location'],config['openweathermap']['key'])

###############################################################
# MQTT      
mqtt_client = None
prefix = 'simu/' if SIMULATION else ''
MQTT_BROKER = config['mqtt']['broker_ip'] 
PORT = int(config['mqtt']['port'])
TOPIC_SENSOR_CONSUMPTION =  config['mqtt']['topic_cons'] 
TOPIC_SENSOR_PRODUCTION = config['mqtt']['topic_prod'] 
TOPIC_REGULATION = prefix + config['mqtt']['topic_regul'] 
TOPIC_FORCE = prefix + config['mqtt']['topic_force'] # forced/unforced duration - Can be bind to domotics device topic 
TOPIC_STATUS = prefix + config['mqtt']['topic_status']
 
###############################################################
# DOMOTICZ
TOPIC_DOMOTICZ_IN = prefix + "domoticz/in"
IDX_INJECTION = config['domoticz']['idx_injection']
IDX_GRID = config['domoticz']['idx_grid']

###############################################################
# EVELUATION
# The comparison between power consumption and production is done every N seconds, it must be above the measurement
# rate, which is currently 2.5s with PZEM-004t v3.0  module.
EVALUATION_PERIOD = int(config['evaluate']['period'])
# Consider powers are balanced when the difference is below this value (watts). This helps prevent fluctuations.
BALANCE_THRESHOLD = int(config['evaluate']['balance_threshold'])
# Keep this margin (in watts) between the power production and consumption. This helps in reducing grid consumption
# knowing that there may be measurement inaccuracy.
MARGIN = int(config['evaluate']['margin'])
LOW_ECS_ENERGY_TWO_DAYS = int(config['evaluate']['low_ecs_energy_two_days'])  # minimal power on two days
LOW_ECS_ENERGY_TODAY = int(config['evaluate']['low_ecs_energy_today']) # minimal power for today
if (config['evaluate']['send_injection'].lower() == "true"): 
    SEND_INJECTION = True 
else: SEND_INJECTION = False
if (config['evaluate']['send_grid'].lower() == "true"): 
    SEND_GRID = True 
else: SEND_GRID = False

###############################################################
# FUNCTIONS

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
    #debug(1, "Subscribing " + TOPIC_REGULATION_MODE)
    client.subscribe(TOPIC_SENSOR_CONSUMPTION)
    client.subscribe(TOPIC_SENSOR_PRODUCTION)
    client.subscribe("smeter/pzem/ECS")
    if(TOPIC_FORCE != "None"):
        debug(1, "Subscribing " + TOPIC_FORCE)
    global equipments
    for e in equipments:
        if (e.topic_read_power != None):
            debug(1, "Subscribing " + str(e.topic_read_power))

def on_message(client, userdata, msg):
    # Receive power consumption and production values and triggers the evaluation. We also take into account manual
    # control messages in case we want to turn on/off a given equipment.
    global power_production, power_consumption, last_power_production_date, production_energy
    
    print("[on message] topic : " + msg.topic) if SDEBUG else ''
    try:
        if msg.topic == TOPIC_SENSOR_CONSUMPTION:
            print("[on message]         conso : " + str(power_consumption) + ", prod : " + str(power_production)) if SDEBUG else ''
            j = json.loads(msg.payload.decode())
            power_consumption = int(j['power'])
            evaluate()
        elif msg.topic == TOPIC_SENSOR_PRODUCTION:
            print("[on message]         conso : " + str(power_consumption) + ", prod : " + str(power_production)) if SDEBUG else ''
            j = json.loads(msg.payload.decode())
            power_production = int(j['power'])
            correction = 1
            if last_power_production_date is not None:
                now = now_ts()
                delta = now - last_power_production_date
                production_energy += correction *  power_production * delta / 3600.0
            last_power_production_date = now_ts() 

            if SIMULATION:
                power_production = SIM_PROD
            evaluate()
        elif msg.topic == TOPIC_FORCE: 
            print("[on message]         Forcing...") 
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
        else: # This is topic_read_power msg. Which equipment is 'over loaded'  ?
            for e in equipments:
                if (e.topic_read_power != None) and (not e.is_overed):
                    if (msg.topic == e.topic_read_power):
                        print("[on message]         "+ e.name + " is Overed ? ") if SDEBUG else ''
                        j = json.loads(msg.payload.decode())
                        e.check_over(int(j['power']))

    except:
        print("[on message]         error, message badly formated (e.g. pzem error...)") if SDEBUG else ''

def signal_handler(signal, frame):
    """ End of program handler, set equipments 0W and save status"""
    global equipments
    print ("!! Ctrl+C pressed !!")
    log(0, "[signal_handler] !! Ctrl+C pressed !!") 
    for e in equipments:
        e.set_current_power(0) 
        log(2, e.name + " : set power to 0") 
    time.sleep(2)
    saveStatus() if (config['debug']['use_persistent'].lower() == "true") else ''
    log(0, "Bye")
    sys.exit(0)

def loadStatus():
    global CLOUD_forecast, ECS_energy_today, ECS_energy_yesterday, equipments, production_energy
    data = configparser.ConfigParser()
    log(0, "[loadStatus] loading status")
    try:
        data.read('status.ini')
        CLOUD_forecast = int(data['init']['CLOUD_forecast'])
        ECS_energy_today = int(data['init']['ECS_energy_today'])
        ECS_energy_yesterday = int(data['init']['ECS_energy_yesterday'])
        production_energy = int(data['init']['production_energy'])
        log(2,"CLOUD_forecast : " + str(CLOUD_forecast))
        log(2,"ECS_energy_today : " + str(ECS_energy_today))
        log(2,"ECS_energy_yesterday : " + str(ECS_energy_yesterday))
        log(2,"production_energy : " + str(production_energy))
        for e in equipments:
            log(2, "loading " + e.name)
            try:
                if (data[e.name]['overloaded'].lower() == "true"):
                    log(4, "read overloaded : " + data[e.name]['overloaded'].lower())
                    e.set_over()
                else:
                    e.unset_over()
            except:
                e.unset_over()
            try:
                nrj = data[e.name]['energy']
                if (int(nrj) >= 0):
                    log(4, "read energy : " + nrj)
                    e.set_energy(int(nrj))
            except:
                e.set_energy(0)
    except Exception as e:
        log(1, "Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        log(1, e)
        log(2, "cannot load status.ini")

def saveStatus():
    global CLOUD_forecast, ECS_energy_today, ECS_energy_yesterday
    data = configparser.ConfigParser()
    log(0, "[saveStatus] saving status")
    try:
        data['init'] = {'ECS_energy_today': str(ECS_energy_today),
                        'ECS_energy_yesterday': str(ECS_energy_yesterday),
                        'cloud_forecast': str(CLOUD_forecast),
                        'production_energy': str(int(production_energy))
                        }
        for e in equipments:
            data[e.name] = {'overloaded': str(e.is_overed()),
                            'energy': str(int(e.get_energy()))}
        with open('status.ini', 'w') as statusFile:
            data.write(statusFile)
    except Exception as e:
        log(1, "Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        log(1, e)
        log(2, "cannot save status.ini")
    
def reloadStatus():
    """Reload status on signal handler"""
    # TO BE DONE
    pass

def low_energy_fallback():
    """ Fallback, when the amount of energy today went below a minimum"""

    # This is a custom and very specific fallback method which aim is to turn on the water heater should the daily
    # solar energy income be below a minimum threshold. We want the water to stay warm.
    # The check is done everyday

    global ECS_energy_yesterday, ECS_energy_today, CLOUD_forecast, power_production, equipment_water_heater

    max_power = equipment_water_heater.MAX_POWER
    two_days_nrj = ECS_energy_today + ECS_energy_yesterday
    log(0, '[low_energy_fallback] ECS Energy Yesterday / Today / Sum : {} / {} / {}'.format(ECS_energy_yesterday, ECS_energy_today, two_days_nrj))
    if (equipment_water_heater.is_overed()):
        log(4, "cloud forecast : " + str(CLOUD_forecast))
        log(4, 'ECS Energy has been overloaded today')
        log(4, 'cancelling fallback')
        ECS_energy_today = LOW_ECS_ENERGY_TWO_DAYS
    elif (ECS_energy_today) < LOW_ECS_ENERGY_TODAY:
        if CLOUD_forecast < 20 and two_days_nrj > LOW_ECS_ENERGY_TWO_DAYS:
            log(4, 'cloud forecast is good : {}'.format(CLOUD_forecast))
            log(4, 'there is enough energy stored over 2 days : {}'.format(two_days_nrj))
            log(4, 'cancelling fallback')
        elif CLOUD_forecast > 50 and two_days_nrj < LOW_ECS_ENERGY_TWO_DAYS:
            duration = 3600 * (LOW_ECS_ENERGY_TWO_DAYS - ECS_energy_today) / max_power
            log(4, 'cloud forecast is bad : {}'.format(CLOUD_forecast))
            log(4, 'completing for 2 days, forcing ECS {} to {}W for {} min'.format(equipment_water_heater.name, max_power, int(duration/60)))
            equipment_water_heater.force(max_power, duration)
            debug(0, "--")
        else: # Cloud FORECAST  20 à 50
            duration = 3600 * (LOW_ECS_ENERGY_TODAY - ECS_energy_today) / max_power
            log(4, 'cloud forecast is medium : {}'.format(CLOUD_forecast))
            log(4, 'completing for today, forcing ECS {} to {}W for {} min'.format(equipment_water_heater.name, max_power, int(duration/60)))
            equipment_water_heater.force(max_power, duration)
            debug(0, "--")    

    # save the energy so that it can be used in the fallback check tomorrow
    ECS_energy_yesterday = ECS_energy_today
        
def evaluate():
    # This is where all the magic happen. This function takes decision according to the current power measurements.
    # It examines the list of equipments by priority order, their current state and computes which one should be
    # turned on/off.

    global last_evaluation_date, ECS_energy_today, last_injection, last_grid, CLOUD_forecast
    global equipments, equipment_water_heater, production_energy

    try:
        t = now_ts()
        if last_evaluation_date is not None:
            # reset energy counters every day
            d1 = datetime.datetime.fromtimestamp(last_evaluation_date)
            d2 = datetime.datetime.fromtimestamp(t)
            if d1.hour == 8 and d2.hour == 9: # maybe it has been forced this night (low_energy_fallback)
                equipment_water_heater.unset_overed()

            # d1.hour = 22
            # d2.hour = 23
            if d1.hour == 22 and d2.hour == 23:
                #d1.hour = d2.hour = 23
                log(0,"")
                log(0,"[evaluate] TODAY Cloud / Production / Water_heater")
                log(8, "csv : {} ; {}".format(CLOUD_forecast, ECS_energy_today) )
                CLOUD_forecast = weather.getCloudAvg(TOMORROW)
                log(0,"[evaluate] Cloud Forecast : ", CLOUD_forecast)

            global test
            #if test:
            if d1.day != d2.day: # AT MINUIT
                test = False
                ECS_energy_today = equipment_water_heater.get_energy()
                equipment_water_heater.reset_energy()
                
                # ensure that water stays warm enough
                low_energy_fallback()

                for e in equipments:
                    e.unset_over()
                    
            # ensure there's a minimum duration between two evaluations
            if t - last_evaluation_date < EVALUATION_PERIOD:
                return

        last_evaluation_date = t

        if power_production is None or power_consumption is None:
            return

        debug(0, '')
        debug(0, '[evaluate] evaluating power consumption={}, production={}'.format(power_consumption, power_production))

        # Here starts the real work, compare powers
        if power_consumption > (power_production - MARGIN):
            # TOO CONSUMPTION, POWER IS NEEDED, decrease the load
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
        else:
            # There's PV POWER IN EXCESS, try to increase the load to consume this available power
            available_power = power_production - MARGIN - power_consumption
            debug(0, "[evaluate] increasing global power consumption by {}W".format(available_power))
            for i, e in enumerate(equipments):                
                if available_power <= 0:
                    debug(2, "no more available power")
                    break
                debug(2, "2. examining " + e.name)

                # Check if this equpment is over loaded, this is a temporaly workaround 
                # overloaded if (e.current_power > prod) and (prod < e.max_power)
                if ((e.get_current_power() > power_production) and (power_production < e.MAX_POWER)):
                    debug(4, "[evaluate] this equipment is overed, it cannot load power anymore "+str(e.MIN_POWER))
                    log(1, e.name + " is fully loaded for today") if (not e.is_overed()) else ''
                    e.set_over()
                    continue

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
        # Build Domoticz Messages (Energy Counter Injection and/or Grid) then InfluxDB will be updated too
        injection = (power_consumption - power_production) 
        if injection < 0: # Prepare Injection message
            grid = 0
            if last_grid != 0: # Send 0 grid only if last_grid wasn't zero in order to avoid too many repetitions
                domoticz = "{ \"idx\": " + IDX_GRID + ", \"nvalue\": 0, \"svalue\": \"" + str(grid) + "\"}"
                mqtt_client.publish(TOPIC_DOMOTICZ_IN, domoticz) if SEND_GRID else ''
            domoticz = "{ \"idx\": " + IDX_INJECTION + ", \"nvalue\": 0, \"svalue\": \"" + str(injection) + "\"}"
            mqtt_client.publish(TOPIC_DOMOTICZ_IN, domoticz) if SEND_INJECTION else ''
        else: # Prepare Grid Message, and Zero Injection message   
            grid = injection
            injection = 0
            if last_injection != 0: # Send 0 injection only if last_injection wasn't zero in order to avoid too many repetitions
                domoticz = "{ \"idx\": " + IDX_INJECTION + ", \"nvalue\": 0, \"svalue\": \"" + str(injection) + "\"}"
                mqtt_client.publish(TOPIC_DOMOTICZ_IN, domoticz) if SEND_INJECTION else ''
            domoticz = "{ \"idx\": " + IDX_GRID + ", \"nvalue\": 0, \"svalue\": \"" + str(grid) + "\"}"
            mqtt_client.publish(TOPIC_DOMOTICZ_IN, domoticz) if SEND_GRID else ''   
        print("[evaluate]                    CALCULATED INJECTION :", injection) if SDEBUG else ''
        print("[evaluate]                    CALCULATED GRID      :", grid) if SDEBUG else ''        
        last_injection = injection
        last_grid = grid
        ##########
        # Build a status message
        status = {
            'date': t,
            'date_str': datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S'),
            'power_consumption': power_consumption,
            'power_production': power_production,
            'production_energy': production_energy,
            'injection' : injection,
            'grid' : grid
        }
        power_equipments = 0
        eq = []
        for e in equipments:
            p = e.get_current_power()        
            power_equipments = power_equipments + p             
            eq.append({
                'name': e.name,
                'current_power': 'unknown' if p is None else p,
                'energy': e.get_energy(),
                'over' : e.is_overed(),
                'forced': e.is_forced()
            })
        status['power_equipments'] = power_equipments
        status['power_house'] = power_consumption - power_equipments
        status['equipments'] = eq
        mqtt_client.publish(TOPIC_STATUS, json.dumps(status))
    except Exception as e:
        debug(0,"[evaluate exception]") 
        debug(1, "Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        debug(1, e)

###############################################################
# MAIN

def main():
    global mqtt_client, equipments, equipment_water_heater
    signal.signal(signal.SIGINT, signal_handler) 

    debug(0,"")
    log(0,"")
    log(0,"[Main] Starting PV Power Regulation @" + config['openweathermap']['location'])

    mqtt_client = mqtt.Client()
    equipment.setup(mqtt_client, SIMULATION, prefix)
   
    equipment_water_heater = VariablePowerEquipment('ECS')
    
    # This is a list of EQUIPMENTS BY PRIORITY OREDER (first one has the higher priority). 
    # As many equipments as needed can be listed here.
    equipments = (
        equipment_water_heater,
        # ConstantPowerEquipment('Resille'),
        # UnknownPowerEquipment('plug_1')
    )

    log(0, "Equipments :")
    # At startup, reset everything - Mandatory !
    for e in equipments:
        e.set_current_power(0) 
        log(1, str(e.name) + " set power topic : " + e.topic_set_power)
        log(1, str(e.name) + " read power topic : " + e.topic_read_power)
        log(1, str(e.name) + " power max : " + str(e.MAX_POWER) + " W" )
        log(1, str(e.name) + " power min : " + str(e.MIN_POWER) + " W" )
        log(1, str(e.name) + " percent min : " + str(e.MIN_PERCENT) + " W" )
    
    loadStatus() if (config['debug']['use_persistent'].lower() == "true") else ''
        
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
