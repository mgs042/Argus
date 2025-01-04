import os
from config import set_env_vars
set_env_vars()
from db import gw_alert_database
from flask import Flask
from celery import Celery, shared_task, Task
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from db import gateway_database, device_database, alert_database, gw_alert_database
from location import rev_geocode
from influx import get_influxdb_client

client, bucket, org = get_influxdb_client()
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()


def get_gw_alert_status():
    alerts = []
    result = []
    with gw_alert_database() as db:
        alerts += db.query_alert()
    for alert in alerts:
            result.append((alert[1], alert[3], alert[4], alert[5]))

    return result

print(get_gw_alert_status())


def gw_signal_strength_task():
    gateway_list = []
    with gateway_database() as db:
        gateway_list += db.gateway_query()
    print(gateway_list)
    for gateway in gateway_list:
        signal_values = {
            'rssi': 0,
            'snr': 0
        }
        query = f'''
            from(bucket: "uplink_metrics_log")
            |> range(start: -1h)
            |> filter(fn: (r) => r._measurement == "device_metrics")
            |> filter(fn: (r) => r.gateway_id == "{gateway[2]}")
            |> filter(fn: (r) => r._field == "rssi" or r._field == "snr")  // RSSI Values and SNR
        '''
        result = query_api.query(org=org, query=query)
        if result is not None:
            for table in result:
                sum = 0
                count = 0
                for record in table.records:
                    sum += record.get_value()
                    count += 1
                signal_values[record.get_field()] = sum/count
        print(signal_values)
        if signal_values["rssi"] < 0:
            with gw_alert_database() as db:
                db.alert_write(gateway[1], gateway[2], "Gateway Threshold Breach - RSSI", f'Average RSSI value is {signal_values["rssi"]} in the last 1hr')
        if signal_values["snr"] < 10:
            with gw_alert_database() as db:
                db.alert_write(gateway[1], gateway[2], "Gateway Threshold Breach - SNR", f"Average SNR value is {signal_values["snr"]} in the last 1hr")

gw_signal_strength_task()