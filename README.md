# **Py**thon **S**olar **E**nergy **B**alancer

**The aim is to allocate  solar energy production on multiple equipments (resistive load) in order to improve grid resiliency and reduce homeowner electric bills.**
Equipments priority should be managed.
Communication through _Wifi/Mqtt._

Thanks a lot to ![Pierre](https://github.com/pierrehebert)

**Here is a Pierre's forked version.**

Let update/improve this code to your needs...

![archi](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/doc/archi.png)

## Hardware requirements :

- At least 2  ![Wifi MQTT Energy Smartmeter](https://github.com/Coturex/Wifi_Mqtt_SmartMeter) modules
   - Here a third Pzem Smartmeter is used, connected to the WaterHeater in order to improve Grafana charts and to detect Over Load when the thermostat goes to off/on.
- _n_ ![Wifi MQTT Energy Variator](https://github.com/Coturex/Wifi_Mqtt_PowerVariator) module(s) 
- _n_ Wifi MQTT Energy Commutator (like Sonoff Relay etc...)
- 1 **Raspberry Pi Zero 2 / Pi3 / Pi4**    (which host this python program and Mosquito Mqtt broker)

Installation :

By installing 2 ![Wifi MQTT Energy Smartmeter](https://github.com/Coturex/Wifi_Mqtt_SmartMeter) in your solar system, and clamping the first PZEM toroid  onto main house loads and the second PZEM toroid onto solar inverter, you can monitor &quot;Grid Consumption Energy&quot; (the energy consumed from the grid), &quot; Solar Production Energy&quot; (the energy producted by solar panels), and &quot;Exported Energy&quot; (the calculated energy exported to the grid) 

![→ Installation](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/doc/installation_1.png)


![→ Compteur](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/doc/installation_2.png)

You can monitor the energy flow of the solar system, as following ;

![→ Grafana](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/doc/grafana_screenshot2.png)

Above, Grafana screenshot. (here EDF is the Grid Consumtion Energy)
 
![→ Domoticz](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/doc/domoticz.png)

Above, Domoticz screenshot (from domoticz's page called 'Floorplans') 

## Python requirements :
- python 3
- paho-mqtt : $> pip3 install paho-mqtt

## Features - Addons
  _Pierre vs Coturex_
- At startup it **Calculate** 'Polynomial Regression' **Vector'** depending on Power Variator technology and differents calibrations/equipment **directly from CSV calibration files**   -> implemented in _VariablePowerEquipment_ subclass
- Do ![calibration](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/tree/main/calibration) through Mqtt _(instead of pzem hardware attachment)_
- Read !['Config file'](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/config.ini.sample) at startup (all parameters/settings are located in this file)
- **Dynamic load of equipments** (_rules_ in !['Config file'](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/config.ini.sample))
- Save/Load 'status of equipments' while restarting the program 
   (and every xx seconds cf. 'status_time' in ![Config file](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/config.ini.sample))
- **Cloud forecast**, using OpenWeatherMap (https://openweathermap.org/)
- 'Water heater fallback' if not enough dayly or 2days solar energy : **Seasons consideration**

## Todo - ideas :
 - attach the (un)forced mode to _MQTT Domoticz device_ - _https://www.domoticz.com/wiki/MQTT_

-------

### _My topic mapping :_

  **Python Regulation**
  
      - regul/mode/{(un)forced mode.json}
      
      - regul/status/{evaluate status.json}   

  **Wifi_MQTT_Energy_Smartmeter** : (_pzem_topic_ = smeter/pzem)
  
   <pzem_topic>/<pzem_id>/
   
      - smeter/pzem/{boot.json}
   
      - smeter/pzem/id_0/{pzem.json}
   
      - smeter/pzem/id_n/{pzem.json}


   **Wifi_MQTT_Power_Variator :**  (_vload_topic_ = regul/vload)
   
   <vload_topic>/<vload_id>/
             
      - regul/vload/{boot.json}
     
      - regul/vload/id_0/{percent power}
   
      - regul/vload/id_n/{percent power}
      
      ...

   **Constant Power Equipment :** (_cload_topic_ = regul/cload)
   
   <kload_topic>/<kload_id>/
   
      ...
 
   
   **Domoticz link (then influxDb, Grafana) :** _(and Constant Power Equipment too)_
   
      - domoticz/in/{json} 
      - domoticz/out/{json} 
