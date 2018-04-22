#!/usr/bin/env python3

import numpy as np
import threading
import matplotlib

matplotlib.use('TKAgg')
from matplotlib import pyplot as plt
from pythonosc import udp_client

'''
GUI class - draws the charts based on the aggregated netflow data.
'''
class DrawLine():
    def __init__(self, minValF, maxValF, minValS, maxValS):
        self.x = np.linspace(0, 50., num=100)

        self.fig = plt.figure()

        self.ax1 = self.fig.add_subplot(2, 1, 1)
        self.ax2 = self.fig.add_subplot(2, 1, 2)

        self.fig.canvas.draw()

        self.h1, = self.ax1.plot(self.x, lw=3)
        self.h2, = self.ax2.plot(self.x, lw=3)

        self.ax1.set_ylim(minValF, maxValF)
        self.ax2.set_ylim(minValS, maxValS)

        self.ax1background = self.fig.canvas.copy_from_bbox(self.ax1.bbox)
        self.ax2background = self.fig.canvas.copy_from_bbox(self.ax2.bbox)

        self.current1 = [0] * 100
        self.current2 = [0] * 100

        # for i in np.arange(1000):
        self.h1.set_ydata(self.current1)
        self.h2.set_ydata(self.current2)
        self.fig.canvas.restore_region(self.ax1background)
        self.fig.canvas.restore_region(self.ax2background)
        self.ax1.draw_artist(self.h1)
        self.ax2.draw_artist(self.h2)
        self.fig.canvas.blit(self.ax1.bbox)
        self.fig.canvas.blit(self.ax2.bbox)
        plt.pause(0.5)

    def draw(self, x1, x2):
        self.current1.pop(0)
        self.current2.pop(0)

        self.current1.append(x1)
        self.current2.append(x2)

        self.h1.set_ydata(self.current1[0:100])
        self.h2.set_ydata(self.current2[0:100])

        self.fig.canvas.restore_region(self.ax1background)
        self.fig.canvas.restore_region(self.ax2background)

        self.ax1.draw_artist(self.h1)
        self.ax2.draw_artist(self.h2)

        self.fig.canvas.blit(self.ax1.bbox)
        self.fig.canvas.blit(self.ax2.bbox)
        plt.pause(0.00001)


'''
Gets aggregated netflow data and sends it to sonic pi via OSC
'''
class FlowToOsc():
    def __init__(self, host, port):
        self.total_flows = 0
        self.N = 50.0
        self.thresholds = {'udp_pps': 0.0, 'udp_bw': 0.0, 'icmp_pps': 0.0, 'icmp_bw': 0.0, 'tcp_pps': 0.0,
                           'tcp_bw': 0.0}
        self.traffic = []
        self.maxes = {'udp_pps': 0.0, 'udp_bw': 0.0, 'icmp_pps': 0.0, 'icmp_bw': 0.0, 'tcp_pps': 0.0, 'tcp_bw': 0.0}
        self.mins = {'udp_pps': 0.0, 'udp_bw': 0.0, 'icmp_pps': 0.0, 'icmp_bw': 0.0, 'tcp_pps': 0.0, 'tcp_bw': 0.0}
        self.DDOS_THRESHOLD_PERCENTILE = 80
        self.client = udp_client.SimpleUDPClient(host, port)
        self.export = threading.Semaphore(0)

    def update_traffic(self, line):
        self.traffic.append(line)
        self.export.release()
    '''
    Updates the threshold for each traffic type using a sliding window average
    '''
    def update_threshold(self, traffic_type, value):
        window_size = min(self.N, self.total_flows)
        self.thresholds[traffic_type] = (self.thresholds[traffic_type] * window_size + value - self.thresholds[
            traffic_type]) / window_size

    def thresholdize_traffic(self, data_dict, bypass=False):
        if bypass:
            return data_dict
        out = {}

        for k in self.thresholds:
            out[k] = 0.1 if k not in data_dict or float(data_dict[k]) < self.thresholds[k] else 1
        return list(out.values())

    '''
    Scales values to 0-100 range before sending to sonic pi 
    '''
    def scale_multival(self, data_dict, maxes, mins, mintone=0, maxtone=100):
        out = []
        for k in self.thresholds:
            try:
                out.append(float((data_dict)[k]) * (maxtone - mintone) / (maxes[k] - mins[k]))
            except (ZeroDivisionError, KeyError):
                out.append(0)
        return out

    '''
    Waits for aggregated netflow to arrive, then processes it and sends it to Sonic pi
    '''
    def run(self, withGraphics=False):

        if withGraphics:
            monitor = DrawLine(0, 110, 0, 110)
        while(True):
            self.export.acquire()
            self.total_flows += 1
            line = self.traffic.pop(0)
            for traffic_type, value in line.items():
                self.maxes[traffic_type] = max(self.maxes.get(traffic_type) or 0, float(value))
                self.mins[traffic_type] = min(self.mins.get(traffic_type) or 0, float(value))
                self.update_threshold(traffic_type, value)
            print(self.maxes)
            print(self.mins)

            chart_data = self.scale_multival(line, self.maxes, self.mins)

            print("#" + " " + str(chart_data))
            if withGraphics:
                monitor.draw(chart_data[0], chart_data[1])
            self.client.send_message("/note", chart_data)
            self.client.send_message("/amp", self.thresholdize_traffic(line))
