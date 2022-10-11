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

debugger = logging.getLogger('regulation_debug')
debugger.setLevel(logging.DEBUG)

logger = logging.getLogger('regulation_log')
logger.setLevel(logging.INFO)
#flog = logging.basicConfig(level=logging.INFO, filename='app.log', filemode='w') #, format='%(name)s - %(levelname)s - %(message)s')

formatter = logging.Formatter('%(asctime)s - %(message)s')

ch1 = logging.StreamHandler()
ch1.setLevel(logging.DEBUG)
#ch1 = logging.FileHandler('debug.log')
ch1.setFormatter(formatter)
debugger.addHandler(ch1)

ch2 = logging.StreamHandler()
ch2.setLevel(logging.INFO)
ch2 = logging.FileHandler('info.log')
ch2.setFormatter(formatter)
logger.addHandler(ch2)

def debug(indent, msg):
    debugger.debug(('  '*indent)+str(msg))

def log(indent, msg):
    logger.info(('  '*indent)+str(msg))


def main():
    debug(0,"debug")
    log(0,"info")
  
if __name__ == '__main__':
    main()

 
