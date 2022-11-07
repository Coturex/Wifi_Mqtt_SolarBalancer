#!/usr/bin/python3
# 
# Copyright (C) 2018-2019 Pierre Hebert
#                 Mods -> Coturex - F5RQG
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import configparser
config = configparser.ConfigParser()
config.read('config.ini')

debugger = logging.getLogger('regulation_debug')
debugger.setLevel(logging.DEBUG)

logger = logging.getLogger('regulation_log')
logger.setLevel(logging.INFO)
#flog = logging.basicConfig(level=logging.INFO, filename='app.log', filemode='w') #, format='%(name)s - %(levelname)s - %(message)s')

formatter = logging.Formatter('%(asctime)s - %(message)s')

unset_words = ("none", "None", "NONE", "false", "False", "FALSE", "nok", "NOK")

try:
    debug_file_name = config['debug']['debug_file']
    if debug_file_name in unset_words:
        DEBUG = False 
    else:
        DEBUG = True
        ch1 = logging.StreamHandler()
        ch1.setLevel(logging.DEBUG)
        ch1 = logging.FileHandler(debug_file_name)
        ch1.setFormatter(formatter)
        debugger.addHandler(ch1)
except Exception:
    DEBUG = False

try:
    log_file_name = config['debug']['log_file']
    if log_file_name in unset_words:
        LOG = False 
    else:
        LOG = True
        ch2 = logging.StreamHandler()
        ch2.setLevel(logging.INFO)
        ch2 = logging.FileHandler(log_file_name)
        ch2.setFormatter(formatter)
        logger.addHandler(ch2)
except Exception:
    LOG = False

def debug(indent, msg):
    global DEBUG
    if DEBUG:
        debugger.debug(('  '*indent)+str(msg))

def log(indent, msg):
    global LOG
    if LOG:
        logger.info(('  '*indent)+str(msg))


def main():
    debug(0,"debug")
    log(0,"info")
  
if __name__ == '__main__':
    main()

 
