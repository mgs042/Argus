from flask import Flask
from celery import Celery, shared_task, Task
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from db import gateway_database, device_database, alert_database, gw_alert_database
from location import rev_geocode
from influx import get_influxdb_client



def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app


def configure_celery_beat(celery_app: Celery):
    celery_app.conf.beat_schedule = {
        'packet-rate-task': {
            'task': 'celery_tasks.packet_rate_task',  # Reference your task name
            'schedule': 60.0,  # Run every 60 seconds
        },
        'signal-strength-task': {
            'task': 'celery_tasks.signal_strength_task',  # Reference your task name
            'schedule': 60.0,  # Run every 60 seconds
        },
        'gw_signal-strength-task': {
            'task': 'celery_tasks.gw_signal_strength_task',  # Reference your task name
            'schedule': 60.0,  # Run every 60 seconds
        }
    }

client, bucket, org = get_influxdb_client()
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

@shared_task
def update_influx(metrics_data, coordinates, device_addr):
    device_name = metrics_data.get('device_name', 'Unknown')
    device_id = metrics_data.get('device_id', 'Unknown')
    gateway_id = metrics_data.get('gateway_id', 'Unknown')
    rssi = metrics_data.get('rssi', 0)
    snr = metrics_data.get('snr', 0)
    f_cnt = metrics_data.get('f_cnt', -1)
    if f_cnt == 0:
        print("Frame-Count Reset")
        with alert_database() as db:
            db.alert_write(device_name, device_id, "Device Reset", "Frame Count is reset to 0")
    with gateway_database() as db:
            gateway_location = db.fetch_gateway_location(gateway_id)
            gateway_name = db.fetch_gateway_name(gateway_id)
            with device_database() as db1:
                check = db1.check_device_registered(device_id)
                print(check)
                if check == 0:
                    pass
                elif not db1.check_device_addr(device_id):
                    db1.set_dev_addr(device_id, device_addr)
                    print("Device Address Recorded: "+device_name+" --> "+device_addr)
                elif not db1.check_device_gw(device_id):
                    db1.set_dev_gw(device_id, gateway_name)
                    print("Device Gateway Recorded: "+device_name+" --> "+gateway_name)
            if gateway_location is None:
                try:
                    gateway_location = rev_geocode(coordinates['latitude'], coordinates['longitude'], metrics_data.get(gateway_id))
                except KeyError as e:
                    print(f"KeyError encountered: {e}")
                    gateway_location = "Unknown"
            try:
                p = influxdb_client.Point("device_metrics").tag("device_name", device_name).tag("device_id", device_id).tag("gateway_name", gateway_name).tag("gateway_id", gateway_id).tag("gateway_location", gateway_location).field("rssi", rssi).field("snr", snr).field("f_cnt", f_cnt)
                write_api.write(bucket=bucket, org=org, record=p)

                
                # Here, you can implement your database logic (e.g., using SQLAlchemy)
                print(f"Simulating database update for: {metrics_data}")
                return "Metrics and database updated successfully"
            
            except Exception as e:
                return str(e)
            
@shared_task
def packet_rate_task():
    device_list = []
    uplink_interval = []
    packet_rate = {}
    with device_database() as db:
        device_list += db.device_query()
        uplink_interval += db.device_up_int_query()
    for device in device_list:
        query = f'''
        from(bucket: "uplink_metrics_log")
        |> range(start: -15m)
        |> filter(fn: (r) => r._measurement == "device_metrics")
        |> filter(fn: (r) => r.device_id == "{device[2]}")
        |> filter(fn: (r) => r._field == "f_cnt")  // Correct filter syntax
        |> count()
        '''
        result = query_api.query(org=org, query=query)
        # Extract the count value
        if result:
            # result[0].records[0]['_value'] gives you the count directly
            count_value = result[0].records[0]['_value']
            packet_rate[device[2]] = count_value
        else:
            packet_rate[device[2]] = 0
    for interval in uplink_interval:
        if packet_rate[interval[1]] < (interval[2]//60)*15:
            with alert_database() as db:
                print(db.alert_write(interval[0], interval[1], "Packet Loss", f'{packet_rate[interval[1]]} Packets Recieved in the Last 15min'))
        elif packet_rate[interval[1]] > (interval[2]//60)*15:
            with alert_database() as db:
                print(db.alert_write(interval[0], interval[1], "Packet Flooding", f'{packet_rate[interval[1]]} Packets Recieved in the Last 15min'))
        else:
            with alert_database() as db:
                print("Packet Rate Optimum")
                if db.check_alert_registered(interval[1], "Packet Loss"):
                    db.remove_alert(interval[1], "Packet Loss")
                elif db.check_alert_registered(interval[1], "Packet Flooding"):
                    db.remove_alert(interval[1], "Packet Flooding")

@shared_task
def signal_strength_task():
    device_list = []
    with device_database() as db:
        device_list += db.device_query()
    for device in device_list:
        signal_values = {
            'rssi': 0,
            'snr': 0
        }
        query = f'''
            from(bucket: "uplink_metrics_log")
            |> range(start: -1h)
            |> filter(fn: (r) => r._measurement == "device_metrics")
            |> filter(fn: (r) => r.device_id == "{device[2]}")
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
        if signal_values["rssi"] < 0:
            with alert_database() as db:
                print(db.alert_write(device[1], device[2], "Threshold Breach - RSSI", f'Average RSSI value is {signal_values["rssi"]} in the last 1hr'))
        if signal_values["snr"] < 10:
            with alert_database() as db:
                print(db.alert_write(device[1], device[2], "Threshold Breach - SNR", f'Average SNR value is {signal_values["snr"]} in the last 1hr'))

@shared_task
def gw_signal_strength_task():
    gateway_list = []
    with gateway_database() as db:
        gateway_list += db.gateway_query()
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
                db.alert_write(gateway[1], gateway[2], "Threshold Breach - RSSI", f'Average RSSI value is {signal_values["rssi"]} in the last 1hr')
        if signal_values["snr"] < 10:
            with gw_alert_database() as db:
                db.alert_write(gateway[1], gateway[2], "Threshold Breach - SNR", f"Average SNR value is {signal_values["snr"]} in the last 1hr")
