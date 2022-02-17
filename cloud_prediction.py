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

import requests   
import time
import datetime
from pprint import pprint
from debug_log import debug as debug
 
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
        self.energy = 0
        self.data = 0
        self.apiKey = key

    def setLocation(self, location):
        """Set OpenweatherMap location"""
        self.location = location

    def getCloudAvg(self, sDAY):
        """ Return percent Average of clouds, @ UTC 09:00:00, UTC 12:00:00, UTC 13:00:00"""
        """ Average : ((time1+time2+time3)/3)"""
        s = 0
        q = 3
        c1 = self.getCloudHour(sDAY,9)
        c2 = self.getCloudHour(sDAY,12)
        c3 = self.getCloudHour(sDAY,15)
        if (c1 <0):
            q = q - 1
        else:
            s = s + c1
        if (c2 <0):
            q = q - 1
        else:
            s = s + c2
        if (c3 <0):
                q = q - 1
        else:
            s = s + c3
        if q <= 0:
            return -1
        else:
            avg = s/q
            debug(1, "Cloud_prediction, Average : " +  str(avg))
            return (avg)        

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
            #pprint(wdata)
            debug(0, "Cloud_prediction, Request : " + sdate)
            for i in range(0,len(wdata['list'])):
                datei  = wdata['list'][i]['dt_txt']
                cloudi = wdata['list'][i]['clouds']['all']
                #print(i, datei, cloudi, sdate)
                if sdate == datei:  
                    #print(i, datei, sdate, cloudi)
                    debug(1, "Cloud_prediction, Clouds : " + str(cloudi))
                    return cloudi
        except Exception as e:
            return -2
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
    
    weather = Prediction("Chambery",config['openweathermap']['key'])
    weather.getCloudHour(TODAY,18)
    print(weather.getCloudAvg(TOMORROW))
    #weather.getRawData()
   
if __name__ == '__main__':
    main()

 

