#!/usr/bin/python3
## !/usr/bin/env python

# Copyright (C) 2020-2022 Coturex - F5RQG
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

# Fetch clouds data prediction from OpenWeatherMap
# An API key is needed. Create free account. 
#   Nb of request limited by a day.
#   Forecast deep and time sample rate limited to 3 Hours (forecast), 1 our on day weather
#
# Url public request 
# https://openweathermap.org/city/3027422
# Url API request - Today
# https://api.openweathermap.org/data/2.5/weather?q=chambery&units=metric&appid=5b203696597154116db974003cef4259
# Url API request - Forecast Prochaines heures
# https://api.openweathermap.org/data/2.5/forecast?q=chambery&units=metric&appid=5b203696597154116db974003cef4259

import configparser
import requests   
import time
import datetime
from pprint import pprint


from enum import Enum
class Cloud(Enum):
    TODAY = 0
    DEMAIN = 1
    TOMORROW = 1
    DAY0 = 0
    DAY1 = 1
    DAY2 = 2
    DAY3 = 3

class Prediction:
    def __init__(self, name):
        self.name = name
        self.energy = 0
        self.data = 0

    def getApiKey():
        config = configparser.ConfigParser()
        config.read('config.ini')
        return config['openweathermap']['api']

    def fetchData(self, type):
        """Fetch data predictions, return value at UTC Time"""

    def getCloudAvg(DAY):
        """ Return % Average of clouds, @ UTC 09:00:00, UTC 12:00:00, UTC 13:00:00"""
        pass

    def getCloudHour(DAY,H):
        """ Return % of clouds at specific Hour, DAY"""
        pass

    def saveEnergy(self):
        pass
    
    def reset_energy(self):
        pass

    def log(self):
        """ Log cloud prediction, real cloud cover and real day energy production"""
        pass


def get_weather(api_key, location):
    url = "https://api.openweathermap.org/data/2.5/forecast?q={}&units=metric&appid={}.format(location, api_key)"
    r = requests.get(url)
    return r.json()

def main():

    #if len(sys.argv) != 2:
    #    exit("Usage: {} LOCATION".format(sys.argv[0]))
    #location = sys.argv[1]

    location = "Chambery"
    api_key = get_api_key()

    api_key = ""
    weather = get_weather(api_key, location)
   
    for i in range(0,len(weather['list'])):
        print(weather['list'][i]['dt_txt'])
        print(weather['list'][i]['dt'])
        print(weather['list'][i]['clouds']['all'])

    tomorrow =  datetime.date.today() + datetime.timedelta(days=1)
    dt = datetime.datetime(tomorrow.year, tomorrow.month,tomorrow.day, 0, 0, 0)
    print ("tomorrow" , tomorrow)
    ts = int(dt.timestamp())
    print(ts)

   

# https://pymotw.com/3/datetime/

 

#    date_string = "2/11/2021, 04:5:8"

#    date = datetime.datetime.strptime(date_string, "%m/%d/%Y, %H:%M:%S")

#    time_stamp = datetime.datetime.timestamp(date)

#    print(time_stamp)

#    ts1 = int(

    #print ts1

    #pprint(weather)

if __name__ == '__main__':

    main()

 

