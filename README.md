# **Py**thon **S**olar **E**nergy **B**alancer

**The aim is to allocate  solar energy production on multiple equipments (resistive load) in order to improve grid resiliency and reduce homeowner electric bills.**
Equipments priority should be managed.
Communication through _Wifi/Mqtt._

A Python programm called !['regulation.py'](https://github.com/pierrehebert/photovoltaic_optimizer/blob/master/regulation/power_regulation.py) is doing this job. Thanks a lot to ![Pierre](https://github.com/pierrehebert)

 → Main concept : https://www.pierrox.net/wordpress/2019/02/25/optimisation-photovoltaique-2-principe-et-survol-de-la-solution-technique/

Let update/improve this code to your needs...

**Here is a forked version.**

![archi](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/doc/archi.png)

## Hardware requirements :

- 2  ![Wifi MQTT Energy Smartmeter](https://github.com/Coturex/Wifi_Mqtt_SmartMeter) modules
- _n_ ![Wifi MQTT Energy Variator](https://github.com/Coturex/Wifi_Mqtt_PowerVariator) module(s) (... this project is on going...)
- _n_ Wifi MQTT Energy Commutator (like Sonoff Relay etc...)
- 1 **Raspberry Pi Zero 2 / Pi3 / Pi4**    (which host this python program and Mosquito Mqtt broker)

Installation :

By installing 2 ![Wifi MQTT Energy Smartmeter](https://github.com/Coturex/Wifi_Mqtt_SmartMeter) in your solar system, and clamping the first PZEM toroid  onto main house loads and the second PZEM toroid onto solar inverter, you can monitor &quot;Grid Consumption Energy&quot; (the energy consumed from the grid), &quot; Solar Production Energy&quot; (the energy producted by solar panels), and &quot;Exported Energy&quot; (the calculated energy exported to the grid) 

![→ Installation](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/doc/installation.png)

You can monitor the energy flow of the solar system.

![→ Grafana](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/doc/grafana_screenshot1.png) 

![→ Grafana](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/doc/grafana_screenshot2.png)

Grafana screenshots
 
![→ Domoticz](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/doc/domoticz.png)

Domoticz (plan) screenshot

## Python requirements :
- python 3
- paho-mqtt : $> pip3 install paho-mqtt

## Features - Addons
  _Pierre vs Coturex Diff_
- At startup it **Calculate** 'Polynomial Regression' **Vector'** depending on Power Variator technology and differents calibrations/equipment **directly from CSV calibration files**   -> implemented in _VariablePowerEquipment_ subclass
- Do ![calibration](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/tree/main/calibration) through Mqtt _(instead of pzem hardware attachment)_
- Read !['Config file'](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/config.ini.sample) at startup (all parameters are declared in this file)
- Dynamic load of equipments (set in !['Config file'](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/config.ini.sample))
- Save/load 'status of equipments' while restarting the programm (and every xx seconds cf. 'status_time' @![Config file](https://github.com/Coturex/Wifi_Mqtt_SolarBalancer/blob/main/config.ini.sample))

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
   
   **Unknown Power Load :** (_uload_topic_ = regul/uload)
   
   <uload_topic>/<uload_id>/
   
      ...
   
   
   **Domoticz link (then influxDb, Grafana) :**
   
      - domoticz/in/{json} 
      - domoticz/out/{json} 
