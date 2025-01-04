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