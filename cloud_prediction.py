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
# https://api.openweathermap.org/data/2.5/weather?q=chambery&units=metric&appid=HERE_API_KEY_ID
# Url API request - Forecast Prochaines heures
# https://api.openweathermap.org/data/2.5/forecast?q=chambery&units=metric&appid=HERE_API_KEY_ID

import requests   
import sys
import datetime
from pprint import pprint
from debug_log import debug as debug
import numpy as np

TODAY = 0 
DEMAIN = 1
TOMORROW = 1

DAY0 = 0
DAY1 = 1
DAY2 = 2
DAY3 = 3
class Prediction:
    def __init__(self, location, key):
        self.location = location
        self.data = 0
        self.apiKey = key

    def setLocation(self, location):
        """Set OpenweatherMap location"""
        self.location = location

    def getCloudAvg(self, sDAY):
        """ Return percent Average of clouds, @ UTC 09:00:00, UTC 12:00:00, UTC 13:00:00"""
        """ Average : ((time1+time2)/2)"""
        sHour1 = 9
        sHour2 = 12
        try:
            sdate = datetime.date.today() + datetime.timedelta(days=sDAY)
            sdate1 = str(datetime.datetime(sdate.year, sdate.month,sdate.day, sHour1, 0, 0))
            sdate2 = str(datetime.datetime(sdate.year, sdate.month,sdate.day, sHour2, 0, 0))
            url = "https://api.openweathermap.org/data/2.5/forecast?q={}&units=metric&appid={}".format(self.location, self.apiKey)
            #debug(0, "Cloud_prediction, url : " + url)
            wdata = requests.get(url).json()
            # pprint(wdata)
            debug(0, "Cloud_prediction, requesting " + sdate1 + " " + sdate2)
            tCloud = np.array([])
            for i in range(0,len(wdata['list'])):
                datei  = wdata['list'][i]['dt_txt']
                cloudi = wdata['list'][i]['clouds']['all']
                #print(i, datei, cloudi, sdate)
                if sdate1 == datei or sdate2 == datei:  
                    #print(i, datei, sdate, cloudi)
                    debug(10, "Clouds : " + str(cloudi) + " %\n")
                    tCloud = np.append(tCloud, cloudi)
                    if __name__ == '__main__':
                        print("Clouds : " + str(cloudi) + " %\n")        
        except Exception as e:
            print(e)
            print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
            return -404
        try:
            avg = int(np.average(tCloud))
        except Exception as e:
            print(e)
            print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
            return -1
        return avg   

    def getRawData(self):
        """Print JSON data returned by html request"""
        try:
            url = "https://api.openweathermap.org/data/2.5/forecast?q={}&units=metric&appid={}".format(self.location, self.apiKey)
            wdata = requests.get(url).json()
            pprint(wdata)
        except:
            return -1

    def getCloudHour(self, sDAY, sHour):
        """ Return percent of clouds at specific Hour, DAY"""
        try:
            sdate = datetime.date.today() + datetime.timedelta(days=sDAY)
            sdate = str(datetime.datetime(sdate.year, sdate.month,sdate.day, sHour, 0, 0))
            url = "https://api.openweathermap.org/data/2.5/forecast?q={}&units=metric&appid={}".format(self.location, self.apiKey)
            #debug(0, "Cloud_prediction, url : " + url)
            wdata = requests.get(url).json()
            # pprint(wdata)
            debug(0, "Cloud_prediction, requesting " + sdate)
            for i in range(0,len(wdata['list'])):
                datei  = wdata['list'][i]['dt_txt']
                cloudi = wdata['list'][i]['clouds']['all']
                #print(i, datei, cloudi, sdate)
                if sdate == datei:  
                    #print(i, datei, sdate, cloudi)
                    debug(10, "Clouds : " + str(cloudi) + " %\n")
                    return cloudi
        except Exception as e:
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
    weather.getRawData()
    #print("today 9H UTC : " + str(weather.getCloudHour(TODAY,9)))
    #print("today 12H UTC : " + str(weather.getCloudHour(TODAY,12)))
    #print("today 15H UTC : " + str(weather.getCloudHour(TODAY,15)))
    #print("today 18H UTC : " + str(weather.getCloudHour(TODAY,18)))
    #print("tomorrow  9H UTC : " + str(weather.getCloudHour(TOMORROW,9)))
    #print("tomorrow 12H UTC : " + str(weather.getCloudHour(TOMORROW,12)))
    #print("tomorrow 15H UTC : " + str(weather.getCloudHour(TOMORROW,15)))
    #print ("-----------")
    #print("avg (9H+12H)/2 today : " + str(weather.getCloudAvg(TOMORROW)))
    print("---------------------------")
    print("avg (9H+12H)/2 today : " + str(weather.getCloudAvg(TODAY)))
    print("---------------------------")
    print("avg (9H+12H)/2 tomorrow : " + str(weather.getCloudAvg(TOMORROW)))
    print("bye")
   
if __name__ == '__main__':
    main()

 

