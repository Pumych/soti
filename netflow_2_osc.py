#!/usr/bin/env python3

import threading
import time
import argparse
import socketserver
from collector_v9 import ExportPacket
import client_multi_traffic as cmt

'''
A handler for netflow data collector. Handles the collected netflow data and passes it to the Aggregator
'''
class Handler(socketserver.BaseRequestHandler):
    TEMPLATES = {}

    @classmethod
    def set_server_handler(cls, data_handler, host, port):
        cls.data_handler = data_handler
        data_handler.start_thread()
        server = socketserver.UDPServer((host, port), cls)
        return server

    def handle(self):
        data = self.request[0]
        host = self.client_address[0]

        exported_packet = ExportPacket(data, self.TEMPLATES)
        self.TEMPLATES.update(exported_packet.templates)

        self.data_handler.inc()
        current_time = time.time()
        self.data_handler.check_second_passed(current_time)
        self.data_handler.add_val(current_time, [flow.data for flow in exported_packet.flows])
        self.data_handler.print_index()

'''
Aggregates netflow data on a 1 sec basis and passes the aggregated data to the OSC exporter
'''
class Aggregator:
    def __init__(self, exporter):
        self.index = 0
        self.exist = {}
        self.complete = []
        self.second_passed = threading.Semaphore(0)
        self.prev_time = 0
        self.traffic_types = {'1': 'icmp', '6': 'tcp', '17': 'udp'}
        self.traffic_measures = {"_pps": "IN_PKTS", "_bw": "IN_BYTES"}
        self.exporter = exporter

    def start_thread(self):
        t = threading.Thread(target=self.wait_print)
        t.setDaemon(True)
        t.start()
    '''
    Summerizes flows and passes them to the OSC exporter
    '''
    def summerize_flows(self, flows):
        by_proto = {}
        for flow in flows:
            for j in flow:
                proto_name = self.traffic_types[str(j["PROTOCOL"])]
                for aspect, measurement in self.traffic_measures.items():
                    by_proto[proto_name + aspect] = int(j[measurement]) if str(proto_name + aspect) not in by_proto else \
                        by_proto[proto_name + aspect] + int(j[measurement])
        self.exporter.update_traffic(by_proto)

    def inc(self):
        self.index += 1

    def print_index(self):
        print(self.index)

    def get_index(self):
        return self.index

    def add_val(self, time_added, flows):
        self.prev_time = int(time_added)
        self.exist[time_added] = flows

    def print_exist(self):
        print(self.exist)

    '''
    Checks if a second has passed between received netflow data
    If a second had passed - a semaphore is upped
    '''
    def check_second_passed(self, current_time):
        if self.prev_time != 0 and self.prev_time < int(current_time):
            self.complete.append(self.prev_time)
            self.second_passed.release()

    '''
    Waits for enough data to be collected, then aggregates it.
    '''
    def wait_print(self):
        while (True):
            self.second_passed.acquire()
            try:
                if not self.exist or not self.complete:
                    raise KeyError
                current = self.complete.pop(0)
                aggregate = []
                to_erase = []
                for flow in self.exist:
                    if int(flow) == current:
                        aggregate.append(self.exist[flow])
                        to_erase.append(flow)
                self.summerize_flows(aggregate)
                for flow in to_erase:
                    del self.exist[flow]
            except KeyError:
                pass

'''
A server that listens on an interface for netflow data
'''
def server_loop(server):
    try:
        print("Waiting for traffic")
        server.serve_forever(poll_interval=args.poll)
    except (IOError, SystemExit):
        raise
    except KeyboardInterrupt:
        raise


if __name__ == "__main__":

    parsed = argparse.ArgumentParser(description='A netflow collector that sends flow to sonic-pi via OSC')
    parsed.add_argument('--port', '-P', type=int, help='Port address for collector')
    parsed.add_argument('--host', '-H', type=str, help='IP address for collector')
    parsed.add_argument('--poll', '-I', type=int, default=0.5, help='Poll interval')
    parsed.add_argument('--sonicpihost', '-S', type=str, default='172.16.3.27',
                        help='IP address to send flows to over OSC')
    parsed.add_argument('--sonicpiport', '-R', type=int, default=4559, help='Port address to send flows to over OSC')
    parsed.add_argument('--graphics', '-G', type=bool, default=False, help='Display graphics <True|False>')

    args = parsed.parse_args()
    # Set up exporter that sends aggregated netflow to sonic pi via OSC
    exporter = cmt.FlowToOsc(args.sonicpihost, args.sonicpiport)
    # A handler that takes care of netflow data flowing into the collector
    data_handler = Aggregator(exporter)
    print("Creating server on host: {}, port: {}".format(args.host, args.port))
    server = Handler.set_server_handler(data_handler, args.host, args.port)

    # Start a thread that listens on an interface for netflow data
    t = threading.Thread(target=server_loop, args=(server,))
    t.start()

    '''
    Runs the exporter that gets the aggregated netflow data and sends it to sonic pi via OSC
    Also runs the GUI that draws the netflow data charts. Needs to run from the main thread.
    '''
    try:
        exporter.run(args.graphics)
    except (IOError, SystemExit):
        raise
    except KeyboardInterrupt:
        raise
