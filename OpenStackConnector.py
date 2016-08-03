import time
import requests
import threading
import subprocess

from openstack import boot_vm, delete_vm

ssh_options = 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/mpss2016/mpss-repo/hyrise_rcm/ssh_keys/vagrant'

class OSConnector(object):

    def __init__(self, url):
        self.url = url

        self.nodes = []
        self.instances = []

        self.workload_is_set = False
        self.throughput = 0

        self.lock = threading.Lock()

        self.dispatcher = None
        self.master = None

    def set_url(self, url):
        self.url = url

    def connect(self):
        self.connected = True

    def update_nodes_and_instances(self):

        self.lock.acquire()

        instances_info = []
        if self.dispatcher:
            try:
                r = requests.get("http://" + self.dispatcher['ip'] + ":8080/node_info")
                instances_info = r.json()['hosts']
            except requests.ConnectionError:
                print("Dispatcher not available")
        print(instances_info)

        for instance in self.instances:
            queries = 0
            total_time = 0
            throughput = "n.a."
            if instances_info:
                info = [i for i in instances_info if i['ip'] == instance['ip']]
                if len(info) == 1:
                    # not available for dispatcher
                    queries = int(info[0]['total_queries'])
                    total_time = int(info[0]['total_time'])
                    if queries != 0:
                        throughput = "%.2f ms" % (total_time/queries/1000)
                else:
                    print('found duplicate IP')

            instance["throughput"] = throughput
            instance["totalTime"] = total_time
            instance["queries"] = queries

        for instance in self.instances:
            try:
                p = subprocess.Popen([ssh_options + ' vagrant@' + instance['ip'] + ' cat /proc/loadavg'], stdout=subprocess.PIPE,shell=True)
                output = p.communicate()[0]
                instance["load"] = output.split(' ')[0]
            except requests.ConnectionError:
                print("VM %s not available".format(instance['ip']))

        self.lock.release()
        print(self.instances)
        return


    def get_nodes(self):
        return self.nodes

    def get_instances(self):
        return self.instances

    def reset_instances(self):
        self.lock.acquire()
        removed = True
        while removed:
            removed = self.remove_replica()
        delete_vm(self.dispatcher)
        delete_vm(self.master)
        self.nodes = []

        self.dispatcher = None
        self.master = None
        self.lock.release()
        return

    def add_node(self, ip):
        node = {'hostname':ip, 'runningContainers':1}
        self.nodes.append(node)
        return node

    def start_dispatcher(self):
        if not self.dispatcher:
            info = boot_vm('hyrise_dispatcher', 'dispatcher_1')
            info['type'] = 'Dispatcher'
            info['name'] = ''
            info['node'] = info['ip']
            self.instances.append(info)
            self.add_node(info['ip'])
            self.dispatcher = info
        return {"node": self.dispatcher['id'], "ip": self.dispatcher['ip']}

    def start_master(self):
        if not self.master:
            if not self.dispatcher:
                print("Create dispatcher first")
                return {"node":'', "ip":''}
            info = boot_vm('hyrise', 'master_1')
            info['type'] = 'Master'
            info['name'] = ''
            info['node'] = info['ip']
            self.instances.append(info)
            self.add_node(info['ip'])
            self.master = info

            # set dispatcher IP
            #command = ssh_options + ' vagrant@' + info['ip'] + ' echo ' + self.dispatcher_url + ' > /home/vagrant/hyrise_dispatcher/master_IP.conf'
            #p = subprocess.Popen([command], stdout=subprocess.PIPE,shell=True)
        return {"node": self.master['id'], "ip": self.master['ip']}

    def start_replica(self):
        if not self.maste or not self.dispatcher:
            print("First create master and dispatcher")
            return  {"node":'', "ip":''}
        _id = len(self.instances)
        info = boot_vm('hyrise', 'replica_'+str(_id))
        # TODO set dispatcher+master IP
        info['type'] = 'Replica'
        info['name'] = ''
        info['node'] = info['ip']
        self.instances.append(info)
        self.add_node(info['ip'])
        return {"node": info['id'], "ip": info['ip']}
       
    def remove_replica(self):
        self.lock.acquire()
        info = None
        if self.instances and len(self.instances) > 2:
            info = self.instances.pop()
            try:
                requests.get("http://" + self.dispatcher['ip'] + ":8080/remove_node/%s:" % info['ip'], timeout=1)
            except Exception as e:
                print(e)
                delete_vm(info)
        self.lock.release()
        return info

    def get_throughput(self):
        return {"system": [time.time(), self.throughput]}

    def set_workload(self, status):
        print("set workload", status)
        if int(status) == 1:
            self.workload_is_set = True
        else:
            self.workload_is_set = False
        return
