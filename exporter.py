#!/usr/bin/env python3

import argparse
import socket as s
import math
import time
import os
import logging
import statistics
import threading

import prometheus_client
from prometheus_client.samples import Timestamp

from pyparsing import *

from collections import deque
from prometheus_client.core import (
    InfoMetricFamily, GaugeMetricFamily, CounterMetricFamily)
from threading import Thread

# TODO: Errorhandling, Recovery after errors (e.g. rshake sensor temporary unavailable), error counters
# TODO: Logging for SystemD. More logging.
# TODO: Own user/group for service

PROMETHEUS_NAMESPACE = 'rshake'

class RshakeCollector(object):
    """Collector for sensor data."""

    rshakeSensor = None

    def __init__(self, integration_sec, registry=prometheus_client.REGISTRY):
        self.integration_sec = integration_sec

        self.rshakeSensor = RshakeSensor(integration_sec)
        Thread(target=self.rshakeSensor.mainloop).start()

        registry.register(self)

    def collect(self):
        metrics = []

        total_raw_values = CounterMetricFamily(
            PROMETHEUS_NAMESPACE + '_total_raw_values',
            'Total samples received',
            labels=['channel'])
        metrics.append(total_raw_values)

        max_value = GaugeMetricFamily(
            PROMETHEUS_NAMESPACE + '_max_value',
            'Max Raw value in the last integration period',
            labels=['channel'])
        metrics.append(max_value)

        min_value = GaugeMetricFamily(
            PROMETHEUS_NAMESPACE + '_min_value',
            'Min Raw value in the last integration period',
            labels=['channel'])
        metrics.append(min_value)

        zero_offset = GaugeMetricFamily(
            PROMETHEUS_NAMESPACE + '_zero_offset',
            'Estimated offset of raw values from zero',
            labels=['channel'])
        metrics.append(zero_offset)

        for channel in self.rshakeSensor.channels.values():
            total_raw_values.add_metric(
                labels=[channel.name],
                value=channel.total_raw_values,
                timestamp=None)
            if channel.integration_period != 0:
                ts = Timestamp(channel.integration_period, 0)

                max_value.add_metric(
                    labels=[channel.name],
                    value=channel.max_value,
                    timestamp=ts)
                min_value.add_metric(
                    labels=[channel.name],
                    value=channel.min_value,
                    timestamp=ts)
                zero_offset.add_metric(
                    labels=[channel.name],
                    value=channel.zero_offset,
                    timestamp=ts)

        return metrics

class ChannelValue:
    """Class for data values from a seismograph channel"""
    name: str               # e.g. SHZ

    total_raw_values: int   # RAW values received

    integration_period: int # end timestamp of the integration period
    max_value: int          # Max RAW value received in the last integration period
    min_value: int          # Min RAW value received in the last integration period
    zero_offset: int        # Estimated offset of the RAW values from zero

    part_max_value: int     # Max RAW value received in the current integration period
    part_min_value: int     # Min RAW value received in the current integration period
    part_sum_value: int     # Sum of all RAW values
    part_count: int         # Count of all RAW values

class RshakeSensor(object):
    """Read data via UDP from Raspberry Shake (or Boom)"""

    # Protocol:
    # https://manual.raspberryshake.org/udp.html#udp

    sock = None
    integration_sec = 15

    channels = {}
    #channels: Dict[str, ChannelValue] = {}

    count_lock = threading.Lock()
    count = 0
    initialized = False

    def __init__(self, integration_sec):
        self.integration_sec = integration_sec

        port = 8888                                                             # Port to bind to
        hostipF = "/opt/settings/sys/ip.txt"

        file = open(hostipF, 'r')
        host = file.read().strip()
        file.close()

        HP = host + ":" + str(port)
        logging.info("Opening socket for Raspberry Shake UDP data {}".format(HP))

        self.sock = s.socket(s.AF_INET, s.SOCK_DGRAM | s.SO_REUSEADDR)
        self.sock.bind((host, port))

        logging.info("Waiting for data on {}".format(HP))

    def mainloop(self):

        # Sample Data: {'SHZ', 1627378280.954, 980, 933, 781, 1104}
        data_line = (
            Suppress("{")
            + Suppress("'") + Word(alphanums) + Suppress("'") + Suppress(",")
            + delimitedList(pyparsing_common.fnumber, delim=",")
            + Suppress("}")
        )

        half_integration_sec = self.integration_sec // 2

        while True:
            data, addr = self.sock.recvfrom(1024)    # wait to receive data
            logging.debug('RShake UDP data: {}'.format(data))

            parsed = data_line.parseString(data.decode()).asList()
            logging.debug('RShake parsed UDP data: {}'.format(parsed))
            channel_name = parsed[0]
            num_received_values = len(parsed) - 2

            logging.debug('Received in channel {} {} values'.format(channel_name, num_received_values))

            channel_data = self.channels.get(channel_name)
            if channel_data is None:            # first data from a new channel
                logging.info('Receving data for channel {}'.format(channel_name))

                channel_data = ChannelValue()
                channel_data.name = channel_name
                channel_data.total_raw_values = 0
                channel_data.integration_period = 0
                channel_data.max_value = 0
                channel_data.min_value = 0
                channel_data.zero_offset = -2000000000
                channel_data.part_max_value = -2000000000
                channel_data.part_min_value =  2000000000
                channel_data.part_sum_value = 0
                channel_data.part_count = 0
                self.channels[channel_name] = channel_data

            channel_data.total_raw_values += num_received_values
            channel_data.part_count += num_received_values

            i = 2
            while i < len(parsed):
                value = int(parsed[i])
                channel_data.part_sum_value += value
                if value > channel_data.part_max_value:
                    channel_data.part_max_value = value
                if value < channel_data.part_min_value:
                    channel_data.part_min_value = value
                i += 1
            
            timesec = math.floor(time.time()) + half_integration_sec # offset by half the integration time to be inbetween grafana intervals
            last_interval_end = timesec - (timesec % self.integration_sec) - half_integration_sec
            if channel_data.integration_period != last_interval_end:
                #integration period ended

                #complete data
                channel_data.integration_period = last_interval_end
                channel_data.max_value = channel_data.part_max_value
                channel_data.min_value = channel_data.part_min_value

                zero_offset = channel_data.part_sum_value / channel_data.part_count
                if channel_data.zero_offset == -2000000000:
                    channel_data.zero_offset = zero_offset
                else:
                    offset_weight = 0.1
                    channel_data.zero_offset = (
                        (1-offset_weight) * channel_data.zero_offset + 
                        offset_weight * zero_offset)
               
                #start new data
                channel_data.part_max_value = -2000000000
                channel_data.part_min_value =  2000000000
                channel_data.part_sum_value = 0
                channel_data.part_count = 0

            time.sleep(0.01)

if __name__ == '__main__':
    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
#    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    PARSER = argparse.ArgumentParser()
    PARSER.add_argument("--port", help="The port where to expose the exporter (default:9984)", default=9984)
    PARSER.add_argument("--integration", help="Time interval in seconds for collected data. Should be equal to the Prometheus scrape interval (default:15)", default=15)
    ARGS = PARSER.parse_args()

    port = int(ARGS.port)
    integration = int(ARGS.integration)

    RSHAKE_COLLECTOR = RshakeCollector(integration)

    logging.info("Starting exporter on port {}".format(port))
    prometheus_client.start_http_server(port)

    # sleep indefinitely
    while True:
        time.sleep(60)
