#!/bin/python
import sys
import time
from threading import Thread

from flask import *
from flask_socketio import SocketIO, emit

from OpenStackConnector import OSConnector
from query_hyrise import benchmark, query_hyrise


async_mode = 'threading'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread2 = None
connector = OSConnector("")


def background_thread():
    while True:
        time.sleep(1)
        connector.update_nodes_and_instances()
        nodes = connector.get_nodes()
        socketio.emit('nodes', {'data': nodes}, namespace='/hyrise')
        instances = connector.get_instances()
        socketio.emit('instances', {'data': instances}, namespace='/hyrise')


def workload_thread():
    while True:
        if connector.workload_is_set:
            try:
                print("Load data")
                with open('./queries/1_load_docker.json', 'r') as query_f:
                    query = query_f.read()
                    print(query_hyrise(connector.dispatcher['ip'], 8080, query))
                connector.throughput = benchmark(connector.dispatcher['ip'], 8080, './queries/q1.json', 8, 8)
                print("Bench start..")
                connector.throughput = benchmark(connector.dispatcher['ip'], 8080, './queries/q1.json', 32, 96)
                print("Bench stop..")
                throughput = connector.get_throughput()
                socketio.emit('throughput', {'data': throughput}, namespace='/hyrise')
            except Exception as e:
                print "Unexpected error:", e
        time.sleep(1)

# Routes
@app.route('/')
@app.route('/<path:path>')
def index(path=None):
    global thread, thread2
    if thread is None:
        thread = Thread(target=background_thread)
        thread2 = Thread(target=workload_thread)
        thread.daemon = True
        thread.start()
        thread2.daemon = True
        thread2.start()
    return app.send_static_file('index.html')

@app.route('/css/<path:path>')
def css_proxy(path):
    return send_from_directory('static/css', path)

@app.route('/img/<path:path>')
def img_proxy(path):
    return send_from_directory('static/img', path)

@app.route('/node_modules/<path:path>')
def node_proxy(path):
    return send_from_directory('static/node_modules', path)

@app.route('/app/<path:path>')
def app_proxy(path):
    return send_from_directory('static/app', path)

@app.route('/app-ts/<path:path>')
def app_ts_proxy(path):
    return send_from_directory('static/app-ts', path)

# Events
@socketio.on('connect_swarm', namespace='/hyrise')
def test_connect(message):
    connector.set_url(message["url"])
    info = connector.connect()
    emit('connected', {'data': info})

@socketio.on('get_nodes', namespace='/hyrise')
def get_nodes():
    nodes = connector.get_nodes()
    emit('nodes', {'data': nodes})

@socketio.on('get_instances', namespace='/hyrise')
def get_instances():
    instances = connector.get_instances()
    emit('instances', {'data': instances})

@socketio.on('reset_instances', namespace='/hyrise')
def reset_instances():
    status = connector.reset_instances()
    emit('reset', {'data': status})

@socketio.on('start_dispatcher', namespace='/hyrise')
def start_dispatcher():
    status = connector.start_dispatcher()
    emit('dispatcher_started', {'data': status})

@socketio.on('start_master', namespace='/hyrise')
def start_master():
    status = connector.start_master()
    emit('master_started', {'data': status})

@socketio.on('start_replica', namespace='/hyrise')
def start_replica():
    status = connector.start_replica()
    emit('replica_started', {'data': status})

@socketio.on('remove_replica', namespace='/hyrise')
def remove_replica():
    status = connector.remove_replica()
    emit('replica_removed', {'data': status})

@socketio.on('set_workload', namespace='/hyrise')
def set_workload(data):
    status = connector.set_workload(data["status"])
    emit('workload_set', {'data': status})


if __name__ == '__main__':
    socketio.run(app, host="127.0.0.1")
