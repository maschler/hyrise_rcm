#!/usr/bin/env python -u
'''

This script does the following

1. Connect the router to the public network
2. Add a public key
3. Boot a cirros instance
4. Attach a floating IP
5. Return IP

'''
from __future__ import print_function

import datetime
import os.path
import socket
import sys
import time

from novaclient import client as novaclient
from neutronclient.v2_0 import client as neutronclient


auth_url = "http://192.168.27.100:35357/v2.0"
username = "demo"
password = "password"
tenant_name = "demo"
version = 2

neutron = neutronclient.Client(auth_url=auth_url,
                                    username=username,
                                    password=password,
                                    tenant_name=tenant_name)

nova = novaclient.Client(version=version,
                         auth_url=auth_url,
                         username=username,
                         api_key=password,
                         project_id=tenant_name)

def boot_vm(image_name, instance_name, flavor_name='m1.large'):
    print('Create VM...')
    if not nova.keypairs.findall(name="vagrantkey"):
        with open(os.path.expanduser('./ssh_keys/vagrant.pub')) as fpubkey:
            nova.keypairs.create(name="vagrantkey", public_key=fpubkey.read())

    image = nova.images.find(name=image_name)
    flavor = nova.flavors.find(name=flavor_name)
    instance = nova.servers.create(name=instance_name, image=image, flavor=flavor,
                              key_name="vagrantkey")

    # Poll at 5 second intervals, until the status is no longer 'BUILD'
    status = instance.status
    while status == 'BUILD':
        time.sleep(5)
        # Retrieve the instance again so the status field updates
        instance = nova.servers.get(instance.id)
        status = instance.status

    # Get external network
    ext_net, = [x for x in neutron.list_networks()['networks']
                if x['router:external']]

    # Get the port corresponding to the instance
    port, = [x for x in neutron.list_ports()['ports']
             if x['device_id'] == instance.id]

    # Create the floating ip
    args = dict(floating_network_id=ext_net['id'],
            port_id=port['id'])
    ip_obj = neutron.create_floatingip(body={'floatingip': args})

    ip = ip_obj['floatingip']['floating_ip_address']
    ip_id = ip_obj['floatingip']['id']
    
    start = datetime.datetime.now()
    timeout = 60 * 60
    end = start + datetime.timedelta(seconds=timeout)
    port = 22
    connect_timeout = 5
    print("Created VM, waiting to come up...")
    while datetime.datetime.now() < end:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(connect_timeout)
        try:
            s.connect((ip, port))
            s.shutdown(socket.SHUT_RDWR)
            s.close()
            break
        except:
            time.sleep(5)
    return {'id': instance.id, 'ip': ip, 'ip_id': ip_id}

def delete_vm(instance):
    if not instance:
        return

    neutron.delete_floatingip(instance['ip_id'])
    try:
        result = nova.servers.delete(instance['id'])
    except Exception as e:
        print(e)
        result = nova.servers.force_delete(instance['id'])
    return result
