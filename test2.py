#!/usr/bin/env python

# NAME: network_audit
# DESCRIPTION: The minimal program to connect to the tag database and create a mainloop.
import subprocess
import datetime
import time
IP = '8.8.8.8'
LOG_FILE='/mnt/flash/home/root/ping.log'
MAX_DURATION = 8 #3600 * 4
with open(LOG_FILE, 'w') as f:                                                                                                                                               
    p = subprocess.Popen(['/bin/ping', IP], stdout=subprocess.PIPE)                                                                                                          
    result = p.stdout
    start = time.time()                                                                                                                                                      
    line = result.readline()                                                                                                                                                 
    while line:                                                                                                                                                              
        d = datetime.datetime.utcnow()                                                                                                                                       
        f.write('{}  -  {}'.format(d.strftime('%d-%m-%Y %H:%M:%S'), line))                                                                                                   
        f.flush()                                                                                                                                                            
        line = result.readline()                                                                                                                                             
        if time.time() - start > MAX_DURATION:                                                                                                                               
            print('max duration reached')                                                                                                                                    
            break
    p.kill()                                                                                                                                                                 
    p.wait()                                                                                                                                                                 
print('end')                                                                                                                                                                 
time.sleep(2 ** 32)
