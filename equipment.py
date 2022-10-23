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

# This module defines various equipments type depending on their control mechanism and power consumption profile.
# A brief summary of classes defined here:
# - Equipment: base class, with common behaviour and processing (including forcing and energy counter)
# - VariablePowerEquipment: an equipment which load can be controlled from 0 to 100%. It specifically uses the
#       digitally controlled SCR as described here: https://www.pierrox.net/wordpress/2019/03/04/optimisation-photovoltaique-3-controle-numerique-du-variateur-de-puissance/
# - UnknownPowerEquipment: an equipment which load can vary over time. It's controlled like a switch (either on or off).
#       This equipment is however not fully implemented as it has been specialized in the ConstantPowerEquipment below.
# - ConstantPowerEquipment: an equipment which load is fixed and known. It can be controlled like a switch.
#       ConstantPowerEquipment is essentially an optimization of UnknownPowerEquipment as it will allow the regulation
#       loop to match power consumption and production faster.
import time
from os.path import exists
from debug_log import log as log
from debug_log import debug as debug
import numpy as np
from debug_log import debug as debug

import configparser
config = configparser.ConfigParser()
config.read('config.ini')

if (config['debug']['equipment_debug'].lower() == "true"): 
    EDEBUG = True 
else: EDEBUG = False

_mqtt_client = None
_send_commands = True


def setup(mqtt_client, send_commands):
    global _mqtt_client, _send_commands
    _mqtt_client = mqtt_client
    _send_commands = send_commands


def now_ts():
    return time.time()

    
##########################################################################
#PARENT CLASS 
class Equipment:
    def __init__(self, name, topic):
        self.name = name
        self.topic = topic
        self.is_forced_ = False
        self.force_end_date = None
        self.energy = 0
        self.current_power = None
        self.last_power_change_date = None

    def decrease_power_by(self, watt):
        """ Return the amount of power that has been canceled, None if unknown """
        # implement in subclasses
        pass

    def increase_power_by(self, watt):
        """ Return the amount of power that is left to use, None if unknown """
        # implement in subclasses
        pass

    def set_current_power(self, power):
        if self.last_power_change_date is not None:
            now = now_ts()
            delta = now - self.last_power_change_date
            self.energy += self.current_power * delta / 3600.0

        self.current_power = power
        self.last_power_change_date = now_ts()

    def get_current_power(self):
        return self.current_power

    def force(self, watt, duration=None):
        """ Force this equipment to the specified power in watt, for a given duration in seconds (None=forever)"""
        # implement in subclasses, watt may be ignored
        self.is_forced_ = watt is not None
        if duration is None:
            self.force_end_date = None
        else:
            self.force_end_date = now_ts() + duration

    def is_forced(self):
        if self.force_end_date is not None:
            if now_ts() > self.force_end_date:
                self.is_forced_ = False
                self.force_end_date = None
        return self.is_forced_

    def get_energy(self):
        return self.energy

    def reset_energy(self):
        if self.last_power_change_date is not None:
            now = now_ts()
            delta = now - self.last_power_change_date
            self.energy += self.current_power * delta / 3600.0

        previous_energy = self.energy
        self.energy = 0
        self.last_power_change_date = now_ts()

        return previous_energy

##########################################################################
#CHILD CLASS 
class VariablePowerEquipment(Equipment):
    MINIMUM_POWER = 150
    MINIMUM_PERCENT = 4
    POLYREG_DEGREE = 5

    X = Y = None

    def __init__(self, name, topic):
        Equipment.__init__(self, name,topic)
        self.power_tab = []
        self.topic_set_power = self.topic + "/cmd"
        self.type = "variable"        
        calibrationFile = "power_calibration_" + name +".csv"
        try:
            log(0,"Opening CSV : " + calibrationFile)
            #self.max_power = readCSV(calibrationFile)
            self.readCSV(calibrationFile)
        except FileNotFoundError as fnf_error:
            print(fnf_error)
            log(1,fnf_error)
            exit()
        except Exception as e:
            print(calibrationFile + " bad format, delimiter...")
            print(e)
            log(1,calibrationFile + " bad format, delimiter...")
            log(1,e)
            exit()
        global X, Y
        self.poly_reg = np.poly1d(np.polyfit(X,Y, VariablePowerEquipment.POLYREG_DEGREE))
        self.max_power= int(self.poly_reg(100))
        # Remplissage du tableau de puissance 
        for percent in np.arange(100, -0.5, -0.5):
            P = (self.poly_reg(percent))
            self.power_tab.append(P)
        self.power_tab.reverse()    
        if EDEBUG:
            print(self.power_tab)  
            time.sleep(5)

    def readCSV(self, csv_file):   # return MAX Power
        global X, Y
        with open(csv_file) as file_name:
            array = np.loadtxt(file_name, delimiter=";")
        X = list(tuple(x[0] for x in array))
        Y = list(tuple(x[1] for x in array))
        return(max(Y))
        
    def power_to_percent(self, value):
        # search nearest value in array using dichotomic method
        # and interpolate return value
        x = int(value)
        n = len(self.power_tab)
        lo = 0
        hi = n - 1
        mid = 0
        if x < 0: return 0
        while lo <= hi:
            mid = (hi + lo) // 2
            if self.power_tab[mid] < x:
                lo = mid + 1
                adj = 1
            elif self.power_tab[mid] > x:
                hi = mid - 1
                adj = 0
            else:
                break
        i = mid + adj
        print("Adj = " + str(adj)) if EDEBUG else ''
        if (i >= n): 
            return 100
        else:
            dist = self.power_tab[i] - self.power_tab[i-1]
            print(dist)  if EDEBUG else ''
            r = 0.5 / (dist / (int(value) - self.power_tab[i-1] ))
            print(r)  if EDEBUG else ''
            print(str(self.power_tab[i]) + " - " + str(self.power_tab[i-1])) if EDEBUG else ''
            print(str(i/2) + " - " + str((i-1)/2)) if EDEBUG else ''
            print("i = " + str(i))
            return (((i-1)/2+r))

    def power_to_percent_BRUT(self, value):
        for i in range(200):
            if (int(value) < self.power_tab[i]): break
        else:
            print("not found")    
        if (self.power_tab[200] < int(value)): return 100
        else:
            dist = self.power_tab[i] - self.power_tab[i-1]
            print(dist)  if EDEBUG else ''
            r = 0.5 / (dist / (int(value) - self.power_tab[i-1] ))
            print(r)  if EDEBUG else ''
            print(str(self.power_tab[i]) + " - " + str(self.power_tab[i-1])) if EDEBUG else ''
            print(str(i/2) + " - " + str((i-1)/2)) if EDEBUG else ''
            return (((i-1)/2+r))

    def set_current_power(self, power):
        super(VariablePowerEquipment, self).set_current_power(power)
        debug(4, "[CHILD: set-current_power] " + self.name ) if EDEBUG else ''
        if self.current_power == 0:
            percent = 0

        else: 
            debug(4,"[CHILD: set_current_power] z :" + str(z)) if EDEBUG else ''
            percent = self.power_to_percent(power)

        # issue with the regulator, don't go below 4 and force to 0
        if percent < VariablePowerEquipment.MINIMUM_PERCENT:
            percent = 0
        if percent > 100:
            percent = 100

        debug(4, "MQTT Publish :")  if EDEBUG else ''  
        debug(5, "sending power command {}W ({}%) for {}".format(int(self.current_power), str(percent), self.name))
        debug(5, "on topic : " + self.topic_set_power) if EDEBUG else ''
        if _send_commands:
            _mqtt_client.publish(self.topic_set_power, str(percent))

    def decrease_power_by(self, watt):

        if watt >= self.current_power:
            decrease = self.current_power
        else:
            decrease = watt

        if self.current_power - decrease < VariablePowerEquipment.MINIMUM_POWER:
            debug(4, "turning off power because it is below the minimum power: "+str(VariablePowerEquipment.MINIMUM_POWER))
            decrease = self.current_power

        if decrease > 0:
            old = self.current_power
            new = self.current_power - decrease
            self.set_current_power(new)
            debug(4, "decreasing power consumption of {} by {}W, from {} to {}".format(self.name, int(decrease), int(old), int(new)))
        else:
            debug(4, "not decreasing power of {} because it is already at 0W".format(self.name))

        return decrease

    def increase_power_by(self, watt):
        debug(4, "[PARENT: increase power by]") if EDEBUG else ''
        debug(5, "{} currently {}, increase by {} W".format(self.name, self.current_power, int(watt))) if EDEBUG else ''
        if self.current_power + watt >= self.max_power:
            increase = self.max_power - self.current_power
            remaining = watt - increase
        else:
            increase = watt
            remaining = 0
        if self.current_power + increase < VariablePowerEquipment.MINIMUM_POWER:
            debug(4, "not increasing power because it doesn't reach the minimal power: "+str(VariablePowerEquipment.MINIMUM_POWER))
            increase = 0
            remaining = watt
        debug(5, "increase {}, remaining {}".format(int(increase), int(remaining))) if EDEBUG else ''
        if increase == 0:
            debug(4, "status quo")
        elif increase > 0:
            old = self.current_power
            new = self.current_power + increase
            self.set_current_power(new)
            debug(4, "increasing power consumption of {} by {}W, from {} to {}".format(self.name, int(increase) , int(old), int(new)))
        else:
            debug(4, "not increasing power of {} because it is already at maximum power {}W".format(self.name, self.max_power))

        return remaining

    def force(self, watt, duration=None):
        super(VariablePowerEquipment, self).force(watt, duration)
        self.set_current_power(0 if watt is None else watt)

##########################################################################
#CHILD CLASS 
class ConstantPowerEquipment(Equipment):
    def __init__(self, name, nominal_power, topic):
        Equipment.__init__(self, name, topic)
        self.nominal_power = nominal_power
        self.is_on = False
        self.type = "constant"

    def set_current_power(self, power):
        super(ConstantPowerEquipment, self).set_current_power(power)
        self.is_on = power != 0
        msg = '1' if self.is_on else '0'
        if _send_commands:
            _mqtt_client.publish(self.topic, msg, retain=True)
        debug(4, "sending power command {} for {}".format(self.is_on, self.name))

    def decrease_power_by(self, watt):
        if self.is_on:
            debug(4, "shutting down {} with a consumption of {}W to recover {}W".format(self.name, self.nominal_power, watt))
            self.set_current_power(0)
            return self.nominal_power
        else:
            debug(4, "{} with a power of {}W is already off".format(self.name, self.nominal_power))
            return 0

    def increase_power_by(self, watt):
        debug(4, "[CHILD: increase power by]") if EDEBUG else ''
        if self.is_on:
            debug(4, "{} with a power of {}W is already on".format(self.name, self.nominal_power))
            return watt
        else:
            if watt >= self.nominal_power:
                debug(4, "turning on {} with a consumption of {}W to use {}W".format(self.name, self.nominal_power, watt))
                self.set_current_power(self.nominal_power)
                return watt - self.nominal_power
            else:
                debug(4, "not turning on {} with a consumption of {}W because it would use more than the available {}W".format(self.name, self.nominal_power, watt))
                return watt

    def force(self, watt, duration=None):
        super(ConstantPowerEquipment, self).force(watt, duration)
        if watt is not None and watt >= self.nominal_power:
            self.set_current_power(self.nominal_power)
        else:
            self.set_current_power(0)

##########################################################################
#CHILD CLASS 
class UnknownPowerEquipment(Equipment):
    def __init__(self, name, topic):
        Equipment.__init__(self, name, topic)
        self.is_on = False
        self.type = "unknow"

    def send_power_command(self):
        debug(4, "sending power command {} for {}".format(self.is_on, self.name))
        pass

    def decrease_power_by(self, watt):
        if self.is_on:
            self.is_on = False
            debug(4, "shutting down {} with an unknown consumption to recover {}W".format(self.name, watt))
            return None
        else:
            debug(4, "{} with an unknown power is already off".format(self.name))
            return 0

    def increase_power_by(self, watt):
        if self.is_on:
            debug(4, "{} with an unknown power is already on".format(self.name))
            return watt
        else:
            self.is_on = True
            debug(4, "turning on {} with an unknown consumption use {}W".format(self.name, watt))
            return None

    def force(self, watt, duration=None):
        super(UnknownPowerEquipment, self).force(watt, duration)
        if watt is None:
            self.is_on = False
            self.set_current_power(0)
        else:
            self.is_on = True
            self.set_current_power(watt)
