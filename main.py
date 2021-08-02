# Multi Service example
#
# 1) starts/stops some number of services. 
# 2) starts/gets result from a task defined in the service.
#    In this case, the task is to generate psudo random primes inefficiently.
# 3) Given some number of tasks, schedules them on the available services.
# 4) Displays average execution time for all the tasks in
#    'micro seconds per task unit'. Normalized because task time is 'random'.
#
# See the build() method for configuring the number of services or tasks.
#
# DEPENDS ON:
#
# A) kivy==master
#    kivy==2.0.0 has an issue,
#    see https://github.com/Android-for-Python/Android-for-Python-Users#service-lifetime
# B) oscpy  ( minimum 0.6.0 )
#
# Based, in part, on   https://github.com/tshirtman/kivy_service_osc
#
# Source https://github.com/Android-for-Python/Multi-Service-Example


from kivy.app import App
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import Clock
from functools import partial
from oscpy.client import OSCClient
from oscpy.server import OSCThreadServer
from time import time, sleep
from os import cpu_count

if platform == 'android':
    from jnius import autoclass
elif platform in ('linux', 'linux2', 'macos', 'win'):
    from runpy import run_path
    from threading import Thread        
else:
    raise NotImplementedError("service start not implemented on this platform")

KV = '''
BoxLayout:
    orientation: 'vertical'
    BoxLayout:
        size_hint_y: None
        height: '30sp'
        Button:
            text: 'start services'
            on_press: app.start_services()
        Button:
            text: 'start tasks'
            on_press: app.start_tasks()
        Button:
            text: 'stop services'
            on_press: app.stop_services()

    ScrollView:
        Label:
            id: label
            size_hint_y: None
            height: self.texture_size[1]
            text_size: self.size[0], None

'''

class MultiService(App):
    ### Build
    ###################
    def build(self):
        self.server = server = OSCThreadServer()
        server.listen(
            address=b'localhost',
            port=3002,      #### Also hardcoded 3002 in service.py 
            default=True,
        )
        server.bind(b'/result', self.task_finished)
        server.bind(b'/tcip_port', self.save_tcip_port)
        server.bind(b'/echo', self.recieve_echo)
        self.service = None
        self.num_services_ready = 0
        self.clients = []
        self.tcpip_ports = []
        ################# Configure here ################# 
        # num services MUST be <= number in buildozer.spec
        # num services approx upper bound is os.cpu_count
        self.num_buildozer_spec_services = 8
        self.number_of_services = min(6, cpu_count())
        self.number_of_tasks = 20
        ##################################################
        self.root = Builder.load_string(KV)
        return self.root

    ### Manage Services
    ###################
    def start_services(self):
        if not self.service:
            self.active = [False] * self.number_of_services
            for i in range(self.number_of_services):
                self.start_service(i)

    def start_service(self,id):
        if platform == 'android':
            from android import mActivity
            context =  mActivity.getApplicationContext()
            SERVICE_NAME = str(context.getPackageName()) +\
                '.Service' + 'Worker_' + str(id)
            self.service = autoclass(SERVICE_NAME)
            self.service.start(mActivity,'')

        elif platform in ('linux', 'linux2', 'macos', 'win'):
            # Usually 'import multiprocessing'
            # This is for debug of service.py behavior (not performance)
            self.service = Thread(
                target=run_path,
                args=['service.py'],
                kwargs={'run_name': '__main__'},
                daemon=True
            )
            self.service.start()

    def stop_services(self):
        for client in self.clients:
            client.send_message(b'/stop_service', [])
        self.service = None
        self.clients = []
        self.tcpip_ports = []
        self.num_services_ready = 0

    def save_tcip_port(self,message):
        msg = message.decode('utf8')
        if len(self.clients) == self.number_of_services:
            # a service has restarted and reported a tcpip port
            # if it is the same port there is nothing to do
            # else we look for an unresponsive service and replace it. 
            if msg not in self.tcpip_ports:
                self.echoes = []
                for p,c in zip(self.tcpip_ports,self.clients):
                    c.send_message(b'/echo',[p.encode('utf8'),])
                # We dont know how long all the responses will take.
                # Guess 2 sec, this is OK because we wont get any new
                # results from the killed service id
                Clock.schedule_once(partial(self.replace_service,msg),2)
        else:
            self.tcpip_ports.append(msg)
            # Each service listens on its own tcpip port,
            # Make a Client to talk to that service
            self.clients.append(OSCClient(b'localhost',int(msg)))
            # When we get them all
            if len(self.clients) == self.number_of_services:
                self.num_services_ready = self.number_of_services
                self.root.ids.label.text +=\
                    'Started ' + str(self.number_of_services) + ' services\n'

    def recieve_echo(self,message):
        self.echoes.append(message.decode('utf8'))

    ### Replace a killed service
    ############################
    def replace_service(self,msg,dt):
        for p in self.tcpip_ports:
            if p not in self.echoes:
                # replace the port
                id = self.tcpip_ports.index(p)
                self.tcpip_ports[id] = msg
                self.clients[id] = OSCClient(b'localhost',int(msg))
                # if was being used, reuse the restarted service
                # the lost result is replaced with a new result
                if self.active[id] and\
                   self.last_task_number < self.number_of_tasks:
                    self.start_task(int(id))
                return
 
    ### Manage Tasks
    ###################
    def start_tasks(self):
        if self.num_services_ready:
            self.root.ids.label.text +=\
                'Started '+str(self.number_of_tasks)+' tasks, wait.'
            self.result_magnitude = 0
            self.num_results = 0
            self.last_task_number = 0
            self.start_time = time()
            for i in range(min(self.number_of_tasks,
                               self.num_services_ready,
                               self.num_buildozer_spec_services)):
                self.num_services_ready -= 1
                self.last_task_number += 1
                self.start_task(i)
        else:
            self.root.ids.label.text += 'No services available\n'

    def start_task(self, id):
        self.active[id] = True
        self.clients[id].send_message(b'/start_task',
                                      [str(id).encode('utf8'),])

    def task_finished(self,message):
        id, res = message.decode('utf8').split(',')
        # service available
        self.num_services_ready +=1
        self.active[int(id)] = False
        # collect result
        self.result_magnitude += int(res)
        self.num_results += 1
        # new task ?
        if self.last_task_number < self.number_of_tasks:
            self.num_services_ready -= 1
            self.last_task_number += 1
            self.start_task(int(id))
        self.display_result(id, res)

    ### Display results
    ###################
    def display_result(self, id, res):
        if self.root:
            #self.root.ids.label.text += '     ' + id + '   ' + res + '\n'
            self.root.ids.label.text += '.'
            if self.number_of_tasks == self.num_results:
                self.root.ids.label.text += '\n'
                # the tasks have different execution times
                # a task unit is 'execution time'/'prime value'
                msg = str(round((time() - self.start_time)*1000000/\
                                self.result_magnitude))
                msg += ' micro seconds per normalized prime\n'
                self.root.ids.label.text += msg

if __name__ == '__main__':
    MultiService().run()
