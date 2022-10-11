#!/usr/bin/python3
# #!/usr/bin/env python

import json
import numpy as np

import paho.mqtt.client as mqtt
import signal 
import time

import sys
DEBUG = 0

mqtt_client = None
csv_file = None
log_file = None
percent = None   # Fixe la Valeur en Pourcentage [0..100] du variateur de puissance
measuring = 0    # machine d'état
avg_count = 0    # Comptage du nbre de mesure
avg_power = 0    # moyenne (non pondérée)
avg_samples = 12 # Nbre de mesures pour faire la moyenne des puissances
end_power = 100    # Puissance de l'ECS après l'execution du pgm 
step_stabilization = 10   # attente stabilisation en secondes de la puissance entre chaque seuil
start_stabilization = 500 # attente premiere stabilisation à l'allumage de l'ECS à pleine puissance (environ 8 minutes)

TOPIC_READ_POWER =  "smeter/pzem/ECS"
TOPIC_SET_POWER = "regul/vload/ECS/cmd"
MQTT_BROKER = "10.3.141.1"

def on_connect(mqtt_client, userdata, flags, rc):
    mqtt_client.subscribe(TOPIC_READ_POWER)
    print('Connected to mqtt ' + MQTT_BROKER)

def on_pzem_message(client, userdata, msg):
    global percent, avg_power, avg_count, measuring

    if DEBUG : print("[on_pzem_message] avg_count,measuring,percent[" 
                    + str(avg_count) + "," + str(measuring)+ "," + str(percent)+"]")

    if msg.topic == TOPIC_READ_POWER:
        if DEBUG : print("[on_pzem_message] on topic:" + TOPIC_READ_POWER)
        j = json.loads(msg.payload.decode())
        
        try:
            read_power = int(j['power'])
        except Exception:
            print("[on_pzem_message] ###### pzem error detected ######")
            return

        if (avg_count < avg_samples and measuring):
            if DEBUG : print("[on_pzem_message] pwr : " + str(read_power))
            if read_power > 0:
                log = '[on_pzem_message] # read {} W'.format(read_power)
                print (log)
                log_file.write(log)            
                sys.stdout.flush()
                avg_power += read_power
                avg_count += 1
                if DEBUG : print("[on_pzem_message] avg_count : " + str(avg_count))

        if (avg_count >= avg_samples and measuring):
            avg_power /= float(avg_count)
            line = '{};{}\n'.format(percent, avg_power)
            line = line.replace(".", ",")
            print("[on_pzem_message] csvline power,average : " + line)
            log_file.write(line)
            csv_file.write(line)
            sys.stdout.flush()
            avg_power = 0
            avg_count = 0
            measuring = 0

def signal_handler(signal, frame):
    print ("\n!! Ctrl+C pressed !!") 
    print ("ECS Set power : 0 !") 
    mqtt_client.publish(TOPIC_SET_POWER, str("0"))
    time.sleep(5)
    csv_file.close()
    log_file.close()
    print("Calibration results saved on out.csv") 
    print ("Bye.") 
    sys.exit(0)
    
def main():
    global mqtt_client, csv_file, measuring, percent, avg_count, end_power, start_stabilization, step_stabilization
    signal.signal(signal.SIGINT, signal_handler) 

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_pzem_message

    mqtt_client.connect(MQTT_BROKER, 1883, 120)
    mqtt_client.loop_start()
    time.sleep(10)

    csv_file = open("out.csv", "w")
    log_file = open("out.log", "w")
    
    mqtt_client.publish(TOPIC_SET_POWER, str("100"))
    print ("Waiting for stabilization, " + str(start_stabilization)+ " secondes...")
    time.sleep(start_stabilization)   # Attente Premiere stabilisation d'environ 8 minutes

    for percent in np.arange(100, -0.5, -0.5):
        print(percent)  
        log ='# set power to {}%'.format(percent)
        print (log)
        
        mqtt_client.publish(TOPIC_SET_POWER, str(percent))
        time.sleep(step_stabilization) # Attente 'Stabilisation' à chaque changement de puissance
        measuring = 1 
        
        while measuring:    # only on_pzem_message can down it after sample count is done
            pass

    csv_file.close()
    log_file.close()
    print("Calibration results saved on out.csv") 
    print("End of programme")
    print("ECS Set power : " + str(end_power))
    mqtt_client.publish(TOPIC_SET_POWER, str(end_power))
    time.sleep(5)
    # END

if __name__ == "__main__":
    main()


