# **Py**thon **S**olar **E**nergy **B**alancer

The aim is to allocate  solar energy production on multiple devices (resistive load) in order to improve grid resiliency and reduce homeowner electric bills.
Devices priority should be managed.
Communication througth Wifi/Mqtt

A Python programm called !['regulation.py'](https://github.com/pierrehebert/photovoltaic_optimizer/blob/master/regulation/power_regulation.py) is doing this job.

Thanks a lot to ![Pierre](https://github.com/pierrehebert)

→ Python code : https://github.com/pierrehebert/photovoltaic_optimizer/tree/master/regulation

Let update/improve this code to your needs...

## Hardware requirements :

- 2 ![Wifi MQTT Energy Smartmeter](https://github.com/Coturex/Wifi_Mqtt_SmartMeter)
- _'n'_ ![Wifi MQTT Energy Variator](https://github.com/Coturex/Wifi_Mqtt_PowerVariator) (... this project is on going...)
- _'n'_ Wifi MQTT Energy Commutator (like Sonoff Relay etc...)
- 1 Raspberry Pi Zero 2    (which host Mosquito Mqtt broker and python programm)

## Idea box :
 - WebGui to manage Equipments and priority
 - Add multiple 'Polynomial Regression Vector' depending on Power Variator technology and different calibration
 
   maybe use ![pylib sklearn...](https://www.askpython.com/python/examples/polynomial-regression-in-python)
 - etc...
 - 
