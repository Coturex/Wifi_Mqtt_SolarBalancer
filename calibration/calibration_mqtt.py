#!/usr/bin/python3
# #!/usr/bin/env python

import json
import numpy as np

#import paho.mqtt.client as mqtt
import time

import sys

mqtt_client = None
percent = None
avg_power = avg_count = 0
measuring = 0 
csv_file = None
TOPIC_READ_POWER =  "smeter/pzem/ECS"
TOPIC_SET_POWER = "regul/vload/ECS/cmd"
MQTT_BROKER = "10.3.141.1"

def on_connect(mqtt_client, userdata, flags, rc):
    print('Connected to mqtt' + MQTT_BROKER)
    mqtt_client.subscribe(TOPIC_READ_POWER)

def on_pzem_message(client, userdata, msg):
    global percent, avg_power, avg_count, measuring
    if msg.topic == TOPIC_READ_POWER:
        j = json.loads(msg.payload.decode())
        
        if (avg_count < 12 and measuring):
            read_power = int(j['power'])
            if read_power > 1:
                print('# read {}W'.format(read_power))
                sys.stdout.flush()
                avg_power += read_power
                avg_count += 1

        if (avg_count > 12 and measuring):
            avg_power /= float(avg_count)
            line = '{},{}'.format(percent, avg_power)
            print(line)
            sys.stdout.flush()  
            csv_file.write(line)
            avg_power = 0
            avg_count = 0
            measuring = 0

def main():
    global mqtt_client, csv_file
   
    #mqtt_client = mqtt.Client()
    #mqtt_client.on_connect = on_connect
    #mqtt_client.on_message = on_pzem_message

    #mqtt_client.connect(MQTT_BROKER, 1883, 120)
    #mqtt_client.loop_start()

    csv_file = open("out.csv", "w") 
    
    print('percent;power')
   
    for percent in np.arange(100, -0.5, -0.5):
        print(percent)  
        print('# set power to {}%'.format(percent))
        #mqtt_client.publish(TOPIC_SET_POWER, str(percent))
        #time.sleep(6)
        #measuring = 1 
        
        measuring = 0
        while measuring:    # only on_pzem_message can down it after sample count is done
            pass

    csv_file.close()   
    print("Calibration results saved on out.csv") 

if __name__ == "__main__":
    main()
