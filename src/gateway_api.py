import os
import grpc
import json
from chirpstack_api import api
from google.protobuf.json_format import MessageToJson
from datetime import datetime, timedelta
from google.protobuf.timestamp_pb2 import Timestamp

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

def convert_to_readable_format(timestamp_str, offset_hours=5, offset_minutes=30):
    # Parse the ISO 8601 timestamp (e.g., 2024-12-11T10:34:23.225809Z)
    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    
    # Apply the timezone offset (e.g., UTC +5:30 for IST)
    offset = timedelta(hours=offset_hours, minutes=offset_minutes)
    dt = dt + offset
    
    # Convert to a more readable format (e.g., 2024-12-11 16:15:23)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_gateways_status():
    # Get environment variables
    api_token = os.getenv('CHIRPSTACK_APIKEY')
    chirpstack_server = os.getenv('CHIRPSTACK_SERVER')
    auth_token = [("authorization", "Bearer %s" % api_token)]
    """
    Fetches the status of all gateways.
    """
    try:
        with grpc.insecure_channel(chirpstack_server) as channel:
            client = api.GatewayServiceStub(channel)
            req = api.ListGatewaysRequest()
            req.limit = 100  # Limit the number of gateways fetched
            
            # Send request to ChirpStack server
            resp = client.List(req, metadata=auth_token)
            result = {
                "total": resp.total_count,
                "online": 0,
                "offline": 0,
                "never_seen": 0
            }

            for gateway in resp.result:
                try:
                    g = json.loads(MessageToJson(gateway))
                    if g["state"] == "ONLINE":
                        result["online"] += 1
                    else:
                        result["offline"] += 1
                except:
                        result["never_seen"] +=1
            return result
    except grpc.RpcError as e:
        return f"gRPC error: {e.code()} - {e.details()}"
    except Exception as ex:
        return f"An unexpected error occurred: {str(ex)}"



def get_gateway_details(gateway_id):

    # Get environment variables
    api_token = os.getenv('CHIRPSTACK_APIKEY')
    chirpstack_server = os.getenv('CHIRPSTACK_SERVER')
    auth_token = [("authorization", "Bearer %s" % api_token)]
    """
    Fetches the details of a specific gateway by its ID.
    """
    try:
        with grpc.insecure_channel(chirpstack_server) as channel:
            client = api.GatewayServiceStub(channel)
            req = api.ListGatewaysRequest()
            req.limit = 100  # Limit the number of gateways fetched
            
            # Send request to ChirpStack server
            resp = client.List(req, metadata=auth_token)


            # Check if the result list contains the specified gateway_id
            for gateway in resp.result:
                if gateway.gateway_id == gateway_id:
                    result = json.loads(MessageToJson(gateway))
                    resp_json = {
                        "tenantId": result.get("tenantId", "Unknown"),
                        "gatewayId": result.get("gatewayId", "Unknown"),
                        "name": result.get("name", "Unknown"),
                        "location": result.get("location", "Unknown"),
                        "properties": result.get("properties", {"region_common_name": "Unknown"}),
                        "createdAt": convert_to_readable_format(result.get("createdAt", "")) if result.get("createdAt") else "Unknown",
                        "updatedAt": convert_to_readable_format(result.get("updatedAt", "")) if result.get("updatedAt") else "Unknown",
                        "lastSeenAt": convert_to_readable_format(result.get("lastSeenAt", "")) if result.get("lastSeenAt") else "Unknown",
                        "state": result.get("state", "Unknown")
                    }
                    return resp_json
    
            # If the gateway_id is not found
            return f"Gateway ID {gateway_id} not found in the list."

    except grpc.RpcError as e:
        return f"gRPC error: {e.code()} - {e.details()}"
    except Exception as ex:
        return f"An unexpected error occurred: {str(ex)}"


def get_gateway_metrics(gateway_id):

    api_token = os.getenv('CHIRPSTACK_APIKEY')
    chirpstack_server = os.getenv('CHIRPSTACK_SERVER')
    auth_token = [("authorization", "Bearer %s" % api_token)]

    # Current time in Indian Standard Time (IST)
    end_time_ist = datetime.now()

    # Subtract 5 hours and 30 minutes to get UTC
    end_time_utc = end_time_ist - timedelta(hours=5, minutes=30)

    # Start time as 1 hour ago (adjusted to UTC)
    start_time_utc = end_time_utc - timedelta(hours=6)

    # Convert datetime to Timestamp (Protobuf Timestamp format)
    start_timestamp = Timestamp()
    start_timestamp.FromDatetime(start_time_utc)

    end_timestamp = Timestamp()
    end_timestamp.FromDatetime(end_time_utc)

    # Create the gRPC request
    req = api.GetGatewayMetricsRequest(
        gateway_id=gateway_id,
        start=start_timestamp,
        end=end_timestamp
    )
    
    # Call gRPC service
    try:
        with grpc.insecure_channel(chirpstack_server) as channel:
            client = api.GatewayServiceStub(channel)
            resp = client.GetMetrics(req, metadata=auth_token)
            
        if not resp:
            print("No data returned for the given time range.")
            return None
        print(f"Fetching metrics for gateway ID: {gateway_id}")
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