#!/usr/bin/python3
import datetime
import json
import time
import signal, sys
import paho.mqtt.client as mqtt

from debug_log import log as log
from debug_log import debug as debug

def now_ts():
        return time.time()

def signal_handler(sig, frame):
        """ End of program handler, set equipments 0W and save status"""
        signal_name = '(unknown)'
        if sig == signal.SIGINT:
                signal_name = 'SIGINT'
        if sig == signal.SIGTERM:
                signal_name = 'SIGTERM'
        if sig == signal.SIGUSR1:
                signal_name = 'SIGUSR1'
        print(signal_name + " detected")
        log(0, signal_name + " detected")
        print("Bye")
        sys.exit(0) 

###############################################################
# MAIN
last_ts = 0

def main():
    global last_ts
    signal.signal(signal.SIGINT, signal_handler) 
    signal.signal(signal.SIGHUP, signal_handler) 
    signal.signal(signal.SIGUSR1, signal_handler)


    debug(0,"")
    log(0,"")
    log(0,"[Main] Starting PV TEST") 

    while True:
        print (".")
        time.sleep(5)

if __name__ == '__main__':
    main()
