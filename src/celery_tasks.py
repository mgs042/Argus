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
        'dev_packet-rate-task': {
            'task': 'celery_tasks.dev_packet_rate_task',  # Reference your task name
            'schedule': 60.0,  # Run every 60 seconds
        },
        'gw_packet-rate-task': {
            'task': 'celery_tasks.gw_packet_rate_task',  # Reference your task name
            'schedule': 60.0,  # Run every 60 seconds
        },
        'dev_signal-strength-task': {
            'task': 'celery_tasks.dev_signal_strength_task',  # Reference your task name
            'schedule': 300.0,  # Run every 300 seconds
        },
        'gw_signal-strength-task': {
            'task': 'celery_tasks.gw_signal_strength_task',  # Reference your task name
            'schedule': 300.0,  # Run every 300 seconds
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
            db.alert_write(device_name, device_id, "Device Reset", "Frame Count is reset to 0", 'critical')
    with gateway_database() as db:
            gateway_location = db.fetch_gateway_location(gateway_id)
            gateway_name = db.fetch_gateway_name(gateway_id)
            try:
                lat, long, alt = str(db.fetch_gateway_coordinates(gateway_id)).split(',')
            except:
                lat = long = alt = ''
            with device_database() as db1:
                check = db1.check_device_registered(device_id)
                if check == 0:
                    pass
                elif not db1.check_device_addr(device_id):
                    db1.set_dev_addr(device_id, device_addr)
                    print("Device Address Recorded: "+device_name+" --> "+device_addr)
                elif not db1.check_device_gw(device_id):
                    db1.set_dev_gw(device_id, gateway_id)
                    print("Device Gateway Recorded: "+device_name+" --> "+gateway_name)
            if coordinates != {}:
                if lat == '' and long == '' and alt == '':
                     with gateway_database() as db:
                        db.set_gateway_coord(gateway_id, f'{lat},{long},{alt}')
                elif coordinates['latitude'] != lat or coordinates['longitude'] != long or coordinates['altitude'] != alt:
                    with gateway_database() as db:
                        db.set_gateway_coord(gateway_id, f'{lat},{long},{alt}')
                    with gw_alert_database() as db:
                        print(db.alert_write(gateway_name, gateway_id, 'Gateway Location Changed', f'Location of {gateway_name} has changed by ({lat-coordinates['latitude']}, {long-coordinates['longitude']}, {alt-coordinates['altitude']})', 'critical'))
                if gateway_location is None:
                    try:
                        gateway_location = rev_geocode(coordinates['latitude'], coordinates['longitude'], metrics_data.get(gateway_id))
                        with gateway_database() as db:
                            db.set_gateway_address(gateway_id, gateway_location)
                    except KeyError as e:
                        print(f"KeyError encountered: {e}")
            try:
                p = influxdb_client.Point("uplink_metrics").tag("device_id", device_id).tag("gateway_id", gateway_id).field("f_cnt", f_cnt).field("rssi", rssi).field("snr", snr)
                write_api.write(bucket=bucket, org=org, record=p)

                
                print(f"Simulating database update for: {metrics_data}")
                return "Metrics and database updated successfully"
            
            except Exception as e:
                return str(e)
            
@shared_task
def dev_packet_rate_task():
    device_list = []
    uplink_interval = []
    packet_rate = {}
    with device_database() as db:
        device_list += db.device_query()
        uplink_interval += db.device_up_int_query()
    for device in device_list:
        query = f'''
        from(bucket: "dev_metrics")
        |> range(start: -15m)
        |> filter(fn: (r) => r._measurement == "avg_device_metrics")
        |> filter(fn: (r) => r.device_id == "{device[2]}")
        |> filter(fn: (r) => r._field == "packet_rate")
        '''
        result = query_api.query(org=org, query=query)
        # Extract the count value
        if result is not None:
            count = 0
            for table in result:
                for record in table.records:
                    count += record.get_value()
            packet_rate[device[2]] = int(count)
        else:
            packet_rate[device[2]] = 0
                
    for interval in uplink_interval:
        if packet_rate[interval[1]] == 0:
            with alert_database() as db:
                print(db.alert_write(interval[0], interval[1], 'Offline', 'No packets were sent in the last 15min', 'high'))
                continue
        else:
            with alert_database() as db:
                if db.check_alert_registered(interval[1], "Offline"):
                        db.remove_alert(interval[1], "Offline")
        if packet_rate[interval[1]] < (900//interval[2]):
            with alert_database() as db:
                print(db.alert_write(interval[0], interval[1], "Packet Loss", f'{packet_rate[interval[1]]} Packets Recieved in the Last 15min', 'medium'))
        elif packet_rate[interval[1]] > (900//interval[2]):
            with alert_database() as db:
                print(db.alert_write(interval[0], interval[1], "Packet Flooding", f'{packet_rate[interval[1]]} Packets Recieved in the Last 15min', 'high'))
        else:
            with alert_database() as db:
                print("Packet Rate Optimum for " + interval[0])
                if db.check_alert_registered(interval[1], "Packet Loss"):
                    db.remove_alert(interval[1], "Packet Loss")
                elif db.check_alert_registered(interval[1], "Packet Flooding"):
                    db.remove_alert(interval[1], "Packet Flooding")

@shared_task
def dev_signal_strength_task():
    device_list = []
    with device_database() as db:
        device_list += db.device_query()
    for device in device_list:
        signal_values = {
            'avg_rssi': None,
            'avg_snr': None
        }
        query = f'''
            from(bucket: "dev_metrics")
            |> range(start: -1h)
            |> filter(fn: (r) => r._measurement == "avg_device_metrics")
            |> filter(fn: (r) => r.device_id == "{device[2]}")
            |> filter(fn: (r) => r._field == "avg_rssi" or r._field == "avg_snr")  // RSSI Values and SNR
        '''
        result = query_api.query(org=org, query=query)
        if result is not None:
            for table in result:
                sum = 0
                count = 0
                for record in table.records:
                    sum += record.get_value()
                    count += 1
                if count == 0:
                    with alert_database() as db:
                        print(db.alert_write(device[1], device[2], 'Offline', 'No packets were sent in the last 1hr', 'high'))
                        continue
                else:
                    with alert_database() as db:
                        if db.check_alert_registered(device[1], "Offline"):
                                db.remove_alert(device[1], "Offline")
                signal_values[record.get_field()] = sum/count

        if signal_values["avg_rssi"] is not None and signal_values["avg_rssi"] < 100:
            with alert_database() as db:
                print(db.alert_write(device[1], device[2], "Threshold Breach - RSSI", f'Average RSSI value is {signal_values["avg_rssi"]} in the last 1hr', 'medium'))
        if signal_values["avg_snr"] is not None and signal_values["avg_snr"]< 100:
            with alert_database() as db:
                print(db.alert_write(device[1], device[2], "Threshold Breach - SNR", f'Average SNR value is {signal_values["avg_snr"]} in the last 1hr', 'high'))



@shared_task
def gw_packet_rate_task():
    gateway_list = []
    packet_rate = {}
    with gateway_database() as db:
        gateway_list += db.gateway_query()
    

    for gateway in gateway_list:
        query = f'''
        from(bucket: "gw_metrics")
        |> range(start: -15m)
        |> filter(fn: (r) => r._measurement == "avg_gateway_metrics")
        |> filter(fn: (r) => r.gateway_id == "{gateway[2]}")
        |> filter(fn: (r) => r._field == "packet_rate")
        '''
        result = query_api.query(org=org, query=query)
        # Extract the count value
        if result is not None:
            count = 0
            for table in result:
                for record in table.records:
                    count += record.get_value()
            packet_rate[gateway[2]] = int(count)
        else:
            packet_rate[gateway[2]] = 0

    for gateway in gateway_list:
        with device_database() as db:
            uplink_intervals = db.gateway_up_int_query(gateway[2])
        count = 0
        for interval in uplink_intervals:
            count += (3600//interval[0])
        if packet_rate[gateway[2]] == 0:
            with gw_alert_database() as db:
                print(db.alert_write(gateway[1], gateway[2], 'Offline', 'No packets were sent in the last 15min', 'high'))
                continue
        else:
            with gw_alert_database() as db:
                if db.check_alert_registered(gateway[2], "Offline"):
                        db.remove_alert(gateway[2], "Offline")
        if packet_rate[gateway[2]] < count:
            with gw_alert_database() as db:
                print(db.alert_write(gateway[1], gateway[2], "Packet Loss", f'{packet_rate[gateway[2]]} Packets Recieved in the Last 15min', 'medium'))
        elif packet_rate[gateway[2]] > count:
            with gw_alert_database() as db:
                print(db.alert_write(gateway[1], gateway[2], "Packet Flooding", f'{packet_rate[gateway[2]]} Packets Recieved in the Last 15min', 'high'))
        else:
            with gw_alert_database() as db:
                print("Packet Rate Optimum for " + gateway[1])
                if db.check_alert_registered(gateway[2], "Packet Loss"):
                    db.remove_alert(gateway[2], "Packet Loss")
                elif db.check_alert_registered(gateway[2], "Packet Flooding"):
                    db.remove_alert(gateway[2], "Packet Flooding")
        
@shared_task
def gw_signal_strength_task():
    gateway_list = []
    with gateway_database() as db:
        gateway_list += db.gateway_query()
    for gateway in gateway_list:
        signal_values = {
            'avg_rssi': None,
            'avg_snr': None
        }
        query = f'''
            from(bucket: "gw_metrics")
            |> range(start: -1h)
            |> filter(fn: (r) => r._measurement == "avg_gateway_metrics")
            |> filter(fn: (r) => r.gateway_id == "{gateway[2]}")
            |> filter(fn: (r) => r._field == "avg_rssi" or r._field == "avg_snr")  // RSSI Values and SNR
        '''
        result = query_api.query(org=org, query=query)
        if result is not None:
            for table in result:
                sum = 0
                count = 0
                for record in table.records:
                    sum += record.get_value()
                    count += 1
                if count == 0:
                    with gw_alert_database() as db:
                        print(db.alert_write(gateway[1], gateway[2], 'Offline', 'No packets were sent in the last 1hr', 'high'))
                        continue
                else:
                    with gw_alert_database() as db:
                        if db.check_alert_registered(gateway[1], "Offline"):
                                db.remove_alert(gateway[1], "Offline")
                signal_values[record.get_field()] = sum/count
        if signal_values["avg_rssi"] is not None and signal_values["avg_rssi"] < 100:
            with gw_alert_database() as db:
                print(db.alert_write(gateway[1], gateway[2], "Threshold Breach - RSSI", f'Average RSSI value is {signal_values["avg_rssi"]} in the last 1hr', 'medium'))
        if signal_values["avg_snr"] is not None and signal_values["avg_snr"]< 100:
            with gw_alert_database() as db:
                print(db.alert_write(gateway[1], gateway[2], "Threshold Breach - SNR", f"Average SNR value is {signal_values["avg_snr"]} in the last 1hr", 'high'))
