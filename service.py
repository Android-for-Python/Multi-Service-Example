# A service example
#
# responds to '\start_task` message (Generates a pseudo random number)
# responds to `\stop_service` message
# responds to `\echo` message
# sends `\result` message
# sends `\tcip_port` message
#
# Source https://github.com/Android-for-Python/Multi-Service-Example

from time import sleep
from threading import Thread
from kivy.utils import platform
from oscpy.server import OSCThreadServer
from oscpy.client import OSCClient
if platform == 'android':
    from jnius import autoclass

from random import random

### Also hardcoded 3002 in main.py
CLIENT = OSCClient('localhost', 3002)

if platform == 'android':
    PythonService = autoclass('org.kivy.android.PythonService')
    PythonService.mService.setAutoRestartService(True)

#### The task, a synthetic example.
def generate_pseudo_random_prime():
    # A task that is slow-ish, make it slower by increasing MAX
    MAX = 40000
    last = 0
    for num in range(1, round(MAX*random())):
        for i in range(2, num):
            if (num % i) == 0:
                break
        else:
            last = num
    return last

def do_task(name):
    result = generate_pseudo_random_prime()
    send_message(b'/result', name + ',' + str(result))

#### messages to app
def send_message(type,message):
    CLIENT.send_message(type, [message.encode('utf8'), ])

#### messages from app
stopped = False

def stop_service():
    if platform == 'android':
        PythonService.mService.setAutoRestartService(False)
    global stopped
    stopped = True

def start_task(message):
    msg = message.decode('utf8')
    # task must be a Thread so that the messages are responsive
    Thread(target=do_task, args=(msg,),daemon=True).start()

def echo(message):
    send_message(b'/echo',message.decode('utf8'))

#### main loop
def message_loop():
    SERVER = OSCThreadServer()
    SERVER.listen('localhost', default=True)
    SERVER.bind(b'/stop_service', stop_service)
    SERVER.bind(b'/start_task', start_task)
    SERVER.bind(b'/echo', echo)
    send_message(b'/tcip_port', str(SERVER.getaddress()[1]))    

    while True:
        sleep(1)
        if stopped:
            break
    SERVER.terminate_server()
    sleep(0.1)
    SERVER.close()
    
if __name__ == '__main__':
    message_loop()
    
