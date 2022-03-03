import configparser
config = configparser.ConfigParser()
config.read('config.ini')

def main():
    print(config['mqtt']['broker_ip'])
    print(config['mqtt']['topic_prod'])
    
    if (config['debug']['simulation'].lower() == "true"):
        SIMULATION = True
    else:
        SIMULATION = False
    SIMULATION = True if (config['debug']['simulation'].lower() == "true") else SIMULATION = False


    if SIMULATION:
        print("simul ok")
    else:
        print("simul nok")
        
if __name__ == '__main__':
    main()

 