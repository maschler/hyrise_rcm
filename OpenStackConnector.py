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

        ## Nodes
        self.lock.acquire()
        try:
            # We need to use a local client here as this command cannot be executed within swarm
            local_docker = Client(base_url='tcp://vm-imdmresearch-keller-01.eaalab.hpi.uni-potsdam.de:2375') # TODO: remove remote IP
            start = local_docker.start(container=container.get('Id'))
            wait = local_docker.wait(container=container.get('Id'))
            output = local_docker.logs(container=container.get('Id'))
            local_docker.remove_container(container=container.get('Id'), force=True)

            # swarm list prints an info line before the actual nodes
            response = [n for n in output.decode("utf-8").split('\n') if "level" not in n]

            print(response)

            if response:
                self.nodes = [{"hostname": n.split('.')[0].replace('keller-', ''), "runningContainers": 0} for n in response if n != ''] # TODO: find a more reliable way to return the hostname

            if self.dispatcher_node_url != "":
                r = requests.get("http://" + self.dispatcher_node_url + ":8080/node_info")
                instances_info = r.json()['hosts']
            else:
                instances_info = None
            print(instances_info)

            ## Instances

            if not self.docker:
                return "Error: not connected to swarm"

            containers = self.docker.containers(all=True, filters={'status': 'running'})
            instances = []
            for container in containers:
                info = self.docker.inspect_container(container=container.get('Id'))

                if "hyrise/dispatcher" in container["Image"]:
                    instances.append({
                        "type": "Dispatcher",
                        "name": container["Names"][0],
                        "node": container["Names"][0].split('/')[1].replace('keller-', ''),
                        "Id": container["Id"],
                        "ip": info["NetworkSettings"]["Networks"]["swarm_network"]["IPAddress"]
                    })
                    self.dispatcher_url = info["NetworkSettings"]["Networks"]["swarm_network"]["IPAddress"]
                    self.dispatcher_node_url = info["Node"]["Addr"].split(':')[0]
                    self.dispatcher_ip = info["Node"]["IP"]

                elif "hyrise/hyrise_nvm" in container["Image"]:
                    swarm_ip = info["NetworkSettings"]["Networks"]["swarm_network"]["IPAddress"]
                    queries = 0
                    total_time = 0
                    throughput = "n.a."
                    if instances_info:
                        info = [i for i in instances_info if i['ip'] == swarm_ip]
                        if len(info) == 1:
                            queries = int(info[0]['total_queries'])
                            total_time = int(info[0]['total_time'])
                            if queries != 0:
                                throughput = "%.2f ms" % (total_time/queries/1000)

                    instances.append({
                        "type": container["Labels"]["type"].capitalize(),
                        "name": container["Names"][0],
                        "node": container["Names"][0].split('/')[1].replace('keller-', ''),
                        "Id": container["Id"],
                        "ip": swarm_ip,
                        "throughput": throughput,
                        "totalTime": total_time,
                        "queries": queries
                    })
            self.instances = instances
            for node in self.nodes:
                node["runningContainers"] = sum(1 for i in instances if i["node"] == node["hostname"])


            for instance in self.instances:
                p = subprocess.Popen(['ssh -i /home/vagrant/hyrise_rcm/ssh_keys/vagrant vagrant@' + instance['ip'] + ' cat /proc/loadavg'], stdout=subprocess.PIPE,shell=True)
                output = p.communicate()[0]
               
                instance["load"] = output.split(' ')[0]
        except Exception as e:
            print(e)
        self.lock.release()


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
        for node in self.nodes:
            node["runningContainers"] = 0

        self.dispatcher_url = ""
        self.dispatcher_id = None
        self.master_url = ""
        self.master_id = None
        self.lock.release()
        return

    def start_dispatcher(self):
        info = boot_vm('hyrise_dispatcher', 'dispatcher_1')
        # TODO create only one dispatcher
        self.dispatcher_url = info['ip']
        self.dispatcher_id = info['id']
        return {"node": self.dispatcher_url, "ip": self.dispatcher_url}

    def start_master(self):
        info = boot_vm('hyrise_master', 'master_1')
        # TODO set dispatcher IP
        self.master_url = info['ip']
        self.master_id = info['id']
        return {"node": self.master_url, "ip": self.master_url}

    def start_replica(self):
        _id = len(self.instances)
        info = boot_vm('hyrise_replica', 'replica_'+str(_id))
        # TODO set dispatcher+master IP
        self.instances.append(info)
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
