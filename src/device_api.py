import grpc
from google.protobuf.json_format import MessageToJson
from chirpstack_api import api
from google.protobuf.timestamp_pb2 import Timestamp
from datetime import datetime, timedelta, timezone
import json
import os
from application_api import get_application_list

def convert_to_readable_format(timestamp_str, offset_hours=5, offset_minutes=30):
    # Parse the ISO 8601 timestamp (e.g., 2024-12-11T10:34:23.225809Z)
    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    
    # Apply the timezone offset (e.g., UTC +5:30 for IST)
    offset = timedelta(hours=offset_hours, minutes=offset_minutes)
    dt = dt + offset
    
    # Convert to a more readable format (e.g., 2024-12-11 16:15:23)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def convert_to_ist(utc_timestamp):
    """
    Convert a UTC timestamp (in string format) to Indian Standard Time (IST).
    Add 5 hours and 30 minutes to the UTC time to get IST.
    """
    # Parse the UTC timestamp string to a datetime object
    utc_datetime = datetime.strptime(utc_timestamp, '%Y-%m-%dT%H:%M:%SZ')
    
    # Add 5 hours to get IST
    ist_datetime = utc_datetime + timedelta(hours=5)
    
    # Return the IST datetime as a string in the same format
    return ist_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')

def checkInactive(last_seen_str):
    # Parse the UTC string to a datetime object
    last_seen_time = datetime.fromisoformat(last_seen_str.rstrip('Z')).replace(tzinfo=timezone.utc)
    # Get the current UTC time with timezone info
    current_time = datetime.now(timezone.utc)

    # Check if the last seen time is within 1 hour of the current time
    time_difference = current_time - last_seen_time

    if abs(time_difference) >= timedelta(hours=1):
        return True
    else:
        return False


def get_dev_list():
    # Get environment variables
    api_token = os.getenv('CHIRPSTACK_APIKEY')
    chirpstack_server = os.getenv('CHIRPSTACK_SERVER')
    
    auth_token = [("authorization", "Bearer %s" % api_token)]
    """
    Fetches the list of a all devices in all applications under all tenants.
    """
    device_list=[]
    with grpc.insecure_channel(chirpstack_server) as channel:
        application_list=get_application_list()
        for application in application_list:
            client = api.DeviceServiceStub(channel)
            req = api.ListDevicesRequest()
            req.limit=100
            req.application_id=application["id"]
            resp = client.List(req, metadata=auth_token)
            device_list += json.loads(MessageToJson(resp))['result']
                
        return device_list
    
def get_dev_status():
    # Get environment variables
    api_token = os.getenv('CHIRPSTACK_APIKEY')

    """
    Fetches the status of a all devices in all applications under all tenants.
    """
    device_list = get_dev_list()
    result = {
                "total": 0,
                "online": 0,
                "offline": 0,
                "never_seen": 0
            }
    result["total"] = len(device_list)
    for device in device_list:
        lastSeenAt = device.get("lastSeenAt", "Unknown")
        if lastSeenAt == "Unknown":
            result["never_seen"] += 1
        elif checkInactive(lastSeenAt):
            result["offline"] += 1
        else:
            result["online"] += 1
            
    return result

            
def get_dev_details(dev_eui):
     # Get environment variables
    api_token = os.getenv('CHIRPSTACK_APIKEY')
    chirpstack_server = os.getenv('CHIRPSTACK_SERVER')
    auth_token = [("authorization", "Bearer %s" % api_token)]
    """
    Fetches the details of a specific device by its ID.
    """
    try:
        with grpc.insecure_channel(chirpstack_server) as channel:
            client = api.DeviceServiceStub(channel)
            req = api.GetDeviceRequest()
            req.dev_eui=dev_eui
            resp = client.Get(req, metadata=auth_token)
        if resp:
            resp_json = json.loads(MessageToJson(resp))
            result = {
                    "deviceId": resp_json["device"].get("devEui","Unknown"),
                    "name": resp_json["device"].get("name","Unknown"),
                    "appId": resp_json["device"].get("applicationId","Unknown"),
                    "devProfileId": resp_json["device"].get("deviceProfileId","Unknown"),
                    "createdAt": convert_to_readable_format(resp_json.get("createdAt", "")) if resp_json.get("createdAt") else "Unknown",
                    "updatedAt": convert_to_readable_format(resp_json.get("updatedAt", "")) if resp_json.get("updatedAt") else "Unknown",
                    "lastSeenAt": convert_to_readable_format(resp_json.get("lastSeenAt", "")) if resp_json.get("lastSeenAt") else "Unknown",
                    "status": resp_json.get("deviceStatus", "Unknown")
            }
            return result
        # If the device_id is not found
        return f"Device ID {dev_eui} not found in the list."

    except grpc.RpcError as e:
        return f"gRPC error: {e.code()} - {e.details()}"
    except Exception as ex:
        return f"An unexpected error occurred: {str(ex)}"
    
def get_device_metrics(device_id):

    api_token = os.getenv('CHIRPSTACK_APIKEY')
    chirpstack_server = os.getenv('CHIRPSTACK_SERVER')
    auth_token = [("authorization", "Bearer %s" % api_token)]

    # Get the current time
    now = datetime.now()

    # Round down to the last completed hour (e.g., 12:30 -> 12:00)
    end_time_utc = now.replace(minute=0, second=0, microsecond=0)

    # Start time as 1 hour ago (adjusted to UTC)
    start_time_utc = end_time_utc - timedelta(hours=7)

    # Convert datetime to Timestamp (Protobuf Timestamp format)
    start_timestamp = Timestamp()
    start_timestamp.FromDatetime(start_time_utc)

    end_timestamp = Timestamp()
    end_timestamp.FromDatetime(end_time_utc)

    # Create the gRPC request
    req = api.GetDeviceLinkMetricsRequest(
        dev_eui=device_id,
        start=start_timestamp,
        end=end_timestamp,
        aggregation=0
    )
    
    # Call gRPC service
    try:
        with grpc.insecure_channel(chirpstack_server) as channel:
            client = api.DeviceServiceStub(channel)
            resp = client.GetLinkMetrics(req, metadata=auth_token)
            
        if not resp:
            print("No data returned for the given time range.")
            return None
        print(f"Fetching metrics for device ID: {device_id}")
        resp_json = json.loads(MessageToJson(resp))
        for key, value in resp_json.items():
            if isinstance(value, dict):  # Check for dicts containing timestamps
                if 'timestamps' in value:
                    value['timestamps'] = [convert_to_ist(ts) for ts in value['timestamps']]
        print(resp_json)
        # Convert gRPC response to JSON format
        return resp_json
    
    except grpc.RpcError as e:
        # Handle gRPC error (e.g., network issues, invalid response, etc.)
        print(f"gRPC error: {e.details()}")
        return None