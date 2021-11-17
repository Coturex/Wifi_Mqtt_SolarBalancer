# **Py**thon **S**olar **E**nergy **B**alancer

The aim is to allocate  solar energy production on multiple equipments (resistive load) in order to improve grid resiliency and reduce homeowner electric bills.
Equipments priority should be managed.
Communication througth _Wifi/Mqtt._

A Python programm called !['regulation.py'](https://github.com/pierrehebert/photovoltaic_optimizer/blob/master/regulation/power_regulation.py) is doing this job.

Thanks a lot to ![Pierre](https://github.com/pierrehebert)

 → Python code : https://github.com/pierrehebert/photovoltaic_optimizer/tree/master/regulation

Let update/improve this code to your needs...

## Hardware requirements :

- 2  ![Wifi MQTT Energy Smartmeter](https://github.com/Coturex/Wifi_Mqtt_SmartMeter)
- _n_ ![Wifi MQTT Energy Variator](https://github.com/Coturex/Wifi_Mqtt_PowerVariator) (... this project is on going...)
- _n_ Wifi MQTT Energy Commutator (like Sonoff Relay etc...)
- 1 Raspberry Pi Zero 2    (which host Mosquito Mqtt broker and python program)

## Idea box :
 - WebGui to manage Equipments and priority, mqtt topic mapping
 - Add multiple 'Polynomial Regression Vector' depending on Power Variator technology and differents calibrations
 
   maybe use ![pylib sklearn...](https://www.askpython.com/python/examples/polynomial-regression-in-python)
 - etc...



-------

### _My topic mapping :_

  **Python Regul Topic**
  
      - regul/mode/{mode.json}
      
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
   
   
   **Domoticz link :**
   
      - domoticz/in/{json} 
