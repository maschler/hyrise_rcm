import time
import requests
import threading
import subprocess

from openstack import boot_vm, delete_vm

class Connector(object):
    def __init__(self, url):
        self.url = url

        self.nodes = []
        self.instances = []

        self.workload_is_set = False
        self.throughput = 0

        self.lock = threading.Lock()

        self.dispatcher_url = ""
        self.master_url = ""

    def set_url(self, url):
        self.url = url

    def connect(self):
        self.connected = True

    def update_nodes_and_instances(self):

        self.lock.acquire()

        if self.dispatcher_url != "":
            r = requests.get("http://" + self.dispatcher_url + ":8080/node_info")
            instances_info = r.json()['hosts']
            print(instance_info)
        else:
            instances_info = None

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
            p = subprocess.Popen(['ssh -i /home/vagrant/hyrise_rcm/ssh_keys/vagrant vagrant@' + instance['ip'] + ' cat /proc/loadavg'], stdout=subprocess.PIPE,shell=True)
            output = p.communicate()[0]
            instance["load"] = output.split(' ')[0]

        self.lock.release()
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
        delete_vm(self.master_id)
        delete_vm(self.dispatcher_id)
        self.nodes = []

        self.dispatcher_url = ""
        self.dispatcher_id = None
        self.master_url = ""
        self.master_id = None
        self.lock.release()
        return

    def add_node(self, ip):
        node = {'hostname':ip, 'runningContainers':1}
        self.nodes.append(node)
        return node

    def start_dispatcher(self):
        info = boot_vm('hyrise_dispatcher', 'dispatcher_1')
        # TODO create only one dispatcher
        self.dispatcher_url = info['ip']
        self.dispatcher_id = info['id']
        info['type'] = 'Dispatcher'
        info['name'] = ''
        info['node'] = info['ip']
        self.instances.append(info)
        self.add_node(info['ip'])
        return {"node": self.dispatcher_id, "ip": self.dispatcher_url}

    def start_master(self):
        info = boot_vm('hyrise_master', 'master_1')
        # TODO set dispatcher IP
        self.master_url = info['ip']
        self.master_id = info['id']

        info['type'] = 'Master'
        info['name'] = ''
        info['node'] = info['ip']
        self.instances.append(info)
        self.add_node(info['ip'])

        return {"node": self.master_id, "ip": self.master_url}

    def start_replica(self):
        _id = len(self.instances)
        info = boot_vm('hyrise_replica', 'replica_'+str(_id))
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
        if self.instances:
            info = self.instances.pop()
            try:
                requests.get("http://" + self.dispatcher_url + ":8080/remove_node/%s:" % info['ip'], timeout=1)
            except Exception as e:
                print(e)
                delete_vm(info['id'])
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
