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
#
# https://wttr.in/chambery?format=j1
#
#  -> JSON format every 3 hours (0 to 7)

import requests   
import sys
import datetime
from pprint import pprint
from debug_log import debug as debug
from debug_log import log as log
import numpy as np

TODAY = 0 
DEMAIN = 1
TOMORROW = 1
AFTERTOMORROW = 2

DAY0 = 0
DAY1 = 1
DAY2 = 2

class Prediction:
    def __init__(self, location, key):
        self.location = location
        self.data = 0
        self.apiKey = key

    def setLocation(self, location):
        """Set location"""
        self.location = location

    def getCloudAvg(self, sDAY):
        """ Return percent Average of clouds, @ UTC 09:00:00, UTC 12:00:00, UTC 13:00:00"""
        """ Average : ((hour1+hour2+hour3)/3 """
        tHours = [3,4,5]
        clouds = 0
        try:
            url = "https://wttr.in/{}?format=j1".format(self.location)
            debug(0, "Cloud_prediction url : " + url)
            wdata = requests.get(url).json()
            # pprint(wdata)
            i = 0
            for h in tHours:
                i += 1 
                debug(0,"[getCloudAvg] sDay {}, h {}".format(int(sDAY), int(h)))
                cloudcoverage = int(wdata['weather'][sDAY]['hourly'][h]['cloudcover'])
                debug(0,"[getCloudAvg] cloudcoverage {}".format(cloudcoverage))
                if __name__ == '__main__':
                    print("Clouds {}H UTC : {} %".format(int(h*3),cloudcoverage)) 
                else:
                    log(10, "Clouds {}H UTC : {} %".format(int(h*3),cloudcoverage))
                clouds += cloudcoverage

        except Exception as e:
            log(1,"*** Error on line {}".format(sys.exc_info()[-1].tb_lineno))
            log(1, e)
            print("*** Error on line {}".format(sys.exc_info()[-1].tb_lineno))
            print(e)
            return -404
        
        try:
            #avg = int(np.average(tCloud))
            avg = int(clouds / i)
        except Exception as e:
            print(e)
            print("*** Error on line {}".format(sys.exc_info()[-1].tb_lineno))
            log(1,"*** Error on line {}".format(sys.exc_info()[-1].tb_lineno))
            log(1, e)
            return -1
        return avg   

    def getRawData(self):
        """Print JSON data returned by html request"""
        try:
            url = "https://wttr.in/{}?format=j1".format(self.location)
            wdata = requests.get(url).json()
            pprint(wdata)
        except:
            return -1

    def getCloudHour(self, sDAY, sHour):
        """ Return percent of clouds at specific Hour, DAY"""
        try:
            url = "https://wttr.in/{}?format=j1".format(self.location)
            wdata = requests.get(url).json()
            # pprint(wdata)
            h = int(sHour/3)
            cloudcoverage = int(wdata['weather'][sDAY]['hourly'][h]['cloudcover'])
            if __name__ == '__main__':
                print("Clouds {}H UTC: {} %".format(int(h*3),cloudcoverage)) 
            return cloudcoverage
        except Exception as e:
            log(1,"*** Error on line {}".format(sys.exc_info()[-1].tb_lineno))
            log(1, e)
            print("*** Error on line {}".format(sys.exc_info()[-1].tb_lineno))
            print(e)
            return -404
        return -1     

    def log(self):
        """ Log cloud prediction, real cloud cover and real day energy production"""
        pass

def main():
    #if len(sys.argv) != 2:
    #    exit("Usage: {} LOCATION".format(sys.argv[0]))
    #location = sys.argv[1]
    import configparser

    config = configparser.ConfigParser()
    config.read('config.ini') 
    
    weather = Prediction(config['openweathermap']['location'],config['openweathermap']['key'])
    #weather.getRawData()
    #print("today 9H UTC : " + str(weather.getCloudHour(TODAY,9)))
    #print("today 12H UTC : " + str(weather.getCloudHour(TODAY,12)))
    print("today 15H UTC : " + str(weather.getCloudHour(TODAY,15)))
    #print("today 18H UTC : " + str(weather.getCloudHour(TODAY,18)))
    #print("tomorrow  9H UTC : " + str(weather.getCloudHour(TOMORROW,9)))
    #print("tomorrow 12H UTC : " + str(weather.getCloudHour(TOMORROW,12)))
    #print("tomorrow 15H UTC : " + str(weather.getCloudHour(TOMORROW,15)))
    #print ("-----------")
    #print("avg (9H+12H)/2 today : " + str(weather.getCloudAvg(TOMORROW)))
    print("---------------------------")
    print("avg UTC(9H+12H+15H)/3 today : " + str(weather.getCloudAvg(TODAY)))
    
    print("---------------------------")
    print("avg UTC(9H+12H+15H)/3 tomorrow : " + str(weather.getCloudAvg(TOMORROW)))
    
    print("bye")
   
if __name__ == '__main__':
    main()

 

