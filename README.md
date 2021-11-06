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

  **Wifi_MQTT_Energy_Smartmeter** : (pzem_topic = smeter/pzem)
  
   <pzem_topic>/<pzem_id>/
   
   - smeter/pzem/{boot.json}
   
   - smeter/pzem/id_0/{status.json}
   
   - smeter/pzem/id_n/{status.json}


   **Wifi_MQTT_Power_Variator :**  (vload_topic = regul/vload)
   
   <vload_topic>/<vload_id>/
   
   - regul/vload/{boot.json}
   
   - regul/vload/id_0/{status.json}
   
   - regul/vload/id_0/**cmd**/{cmd.json}
   
   - regul/vload/id_n/{status.json}
   
   - regul/vload/id_n/**cmd**/{cmd.json}

   **Constant Power Equipment :** 
   
   <kload_topic>/<kload_id>/
   
   - regul/cload/{boot.json}
   
   - regul/cload/id_0/{status.json}
   
   - regul/cload/id_0/**cmd**/{cmd.json}
   
   
   **Unknown Power Load :**
   
   <uload_topic>/<uload_id>/
   
   - regul/uload/{boot.json}
   
   - regul/uload/id_0/{status.json}
   
   - regul/uload/id_0/**cmd**/{cmd.json}
   
   
   **Domoticz link :**
   
   domoticz/in/{json} 
