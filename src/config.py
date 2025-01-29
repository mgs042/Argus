import os
import json
import requests
import grpc
from chirpstack_api import api
from requests.auth import HTTPBasicAuth


# Path to your JSON configuration file
CONFIG_FILE = 'config.json'

def set_config_file(config_var):
    with open(CONFIG_FILE, 'r') as file:
        config = json.load(file)
    for key in config:
        if config[key] != config_var[key] and (config_var[key] != '' and config_var[key] != ':' and config_var[key] != None) :
            config[key] = config_var[key]
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file, indent=4)
    set_env_vars()
    

def check_chirpstack_server_and_api(server_url, api_key):
    """
    Check if the ChirpStack server is running and if the API key is valid using gRPC.

    :param server_url: The base URL of the ChirpStack server (e.g., <IP>:8080).
    :param api_key: The API key for authentication.
    :return: A dictionary with health and API key validity status.
    """
    try:
        ip, port = server_url.split(':')
    except:
        ip = ""
        port = ""
    results = {
        "ip": ip,
        "port": port,
        "server_health": {"reachable": None, "details": None},
        "apikey": api_key,
        "api_key_valid": {"valid": None, "details": None},
    }

    # Check server health using the gRPC ListApplications (or similar) request
    try:
        # Connect to ChirpStack gRPC server
        
        channel = grpc.insecure_channel(server_url)
        auth_token = [("authorization", "Bearer %s" % api_key)]
        client = api.TenantServiceStub(channel)
        req = api.ListTenantsRequest()
        req.limit = 100 #mandatory if you want details
        resp = client.List(req, metadata=auth_token)

        # If we get a successful response, the server is reachable and API key is valid
        results["server_health"]["reachable"] = True
        results["server_health"]["details"] = "ChirpStack server is reachable."
        results["api_key_valid"]["valid"] = True
        results["api_key_valid"]["details"] = "ChirpStack API key is valid."

    except grpc.RpcError as e:
        error = list(str(e.code()).split('.')[1].lower())
        error[0]=error[0].upper()
        error="".join(error)
        results["server_health"]["reachable"] = False
        results["server_health"]["details"] = f"{error}"
        results["api_key_valid"]["valid"] = False
        results["api_key_valid"]["details"] = f"{error}"

    return results
def check_influxdb_server_auth_and_resources(server_url, token, org, bucket):
    """
    Check the InfluxDB server's health, validate the token, and verify the org and bucket names.

    :param server_url: The base URL of the InfluxDB server (e.g., http://<IP>:8086).
    :param token: The API token for authentication.
    :param org: The organization name to validate.
    :param bucket: The bucket name to validate.
    :return: A dictionary with the server health, token validity, and resource verification status.
    """
    ip, port = server_url.split(':')
    results = {
        "ip": ip,
        "port": port,
        "server_health": {"reachable": None, "details": None},
        "apitoken": token,
        "auth_valid": {"valid": None, "details": None},
        "org": org,
        "org_valid": {"valid": None, "details": None},
        "bucket": bucket,
        "bucket_valid": {"valid": None, "details": None},
    }

    headers = {"Authorization": f"Token {token}"}

    # Check server health
    try:
        health_response = requests.get(f"http://{server_url}/health", timeout=5)
        if health_response.status_code != 200 or health_response.json().get("status") != "pass":
            results["server_health"]["reachable"] = False
            results["server_health"]["details"] = health_response.json()
        else:
            results["server_health"]["reachable"] = True
            results["server_health"]["details"] = "InfluxDB server is healthy."
    except requests.RequestException as e:
        e = list(str(e.__class__.__name__))
        error=""+e[0]
        for i in range(1,len(e)):
            if e[i].isupper():
                error+=(" "+e[i])
            else:
                error+=e[i]
        results["server_health"]["reachable"] = False
        results["server_health"]["details"] = error

    # Validate token by querying the orgs endpoint
    try:
        orgs_response = requests.get(f"http://{server_url}/api/v2/orgs", headers=headers, timeout=5)
        if orgs_response.status_code != 200:
            results["auth_valid"]["valid"] = False
            results["auth_valid"]["details"] = orgs_response.json()
        else:
            results["auth_valid"]["valid"] = True
            results["auth_valid"]["details"] = "InfluxDB token is valid."

            # Validate the organization name 
            orgs = orgs_response.json().get("orgs", [])
            if orgs is None:
                results["org_valid"]["valid"] = False
                results["org_valid"]["details"] = "No organizations found in the response."
            elif any(o["name"] == org for o in orgs):
                results["org_valid"]["valid"] = True
                results["org_valid"]["details"] = f"Organization '{org}' is valid."
            else:
                results["org_valid"]["valid"] = False
                results["org_valid"]["details"] = f"Organization '{org}' not found."
    except requests.RequestException as e:
        e = list(str(e.__class__.__name__))
        error=""+e[0]
        for i in range(1,len(e)):
            if e[i].isupper():
                error+=(" "+e[i])
            else:
                error+=e[i]
        results["auth_valid"]["valid"] = False
        results["auth_valid"]["details"] = error
        results["org_valid"]["valid"] = False
        results["org_valid"]["details"] = error
    # Validate the bucket name
    try:
        buckets_response = requests.get(f"http://{server_url}/api/v2/buckets", headers=headers, timeout=5)
        if buckets_response.status_code != 200:
            results["bucket_valid"]["valid"] = False
            results["bucket_valid"]["details"] = buckets_response.json()
        else:
            buckets = buckets_response.json().get("buckets", [])
            if any(b["name"] == bucket for b in buckets):
                results["bucket_valid"]["valid"] = True
                results["bucket_valid"]["details"] = f"Bucket '{bucket}' is valid."
            else:
                results["bucket_valid"]["valid"] = False
                results["bucket_valid"]["details"] = f"Bucket '{bucket}' not found."
    except requests.RequestException as e:
        e = list(str(e.__class__.__name__))
        error=""+e[0]
        for i in range(1,len(e)):
            if e[i].isupper():
                error+=(" "+e[i])
            else:
                error+=e[i]
        results["bucket_valid"]["valid"] = False
        results["bucket_valid"]["details"] = error
    return results

def check_rabbitmq_server(server_url, username='guest', password='guest'):
    """
    Check the RabbitMQ server's health and verify a queue and exchange.

    :param server_url: The base URL of the RabbitMQ server (e.g., http://<IP>:15672/api).
    :return: A dictionary with the server health.
    """
    ip, port = server_url.split(':')
    results = {
        "ip": ip,
        "port": port,
        "server_health": {"reachable": None, "details": None},
    }

    # Check server health using the /api/health endpoint
    try:
        
        ip = server_url.split(':')
        health_response = requests.get(f"http://{ip[0]}:15672/api/health/checks/alarms", auth=HTTPBasicAuth(username, password), timeout=5)

        if health_response.status_code != 200:
            results["server_health"]["reachable"] = False
            results["server_health"]["details"] = health_response.json()
        else:
            results["server_health"]["reachable"] = True
            results["server_health"]["details"] = "RabbitMQ is healthy."
    except requests.RequestException as e:
        e = list(str(e.__class__.__name__))
        error=""+e[0]
        for i in range(1,len(e)):
            if e[i].isupper():
                error+=(" "+e[i])
            else:
                error+=e[i]
        results["server_health"]["reachable"] = False
        results["server_health"]["details"] = error
    return results

def check_telegram_status(botId, chatId):
    """
    Check the validity of Telegram BoT ID and Chat ID.
    """
    results = {
        "botId": botId,
        "chatId": port,
        "server_health": {"reachable": None, "details": None},
    }

    # Check server health using the /api/health endpoint
    try:
        
        ip = server_url.split(':')
        health_response = requests.get(f"http://{ip[0]}:15672/api/health/checks/alarms", auth=HTTPBasicAuth(username, password), timeout=5)

        if health_response.status_code != 200:
            results["server_health"]["reachable"] = False
            results["server_health"]["details"] = health_response.json()
        else:
            results["server_health"]["reachable"] = True
            results["server_health"]["details"] = "RabbitMQ is healthy."
    except requests.RequestException as e:
        e = list(str(e.__class__.__name__))
        error=""+e[0]
        for i in range(1,len(e)):
            if e[i].isupper():
                error+=(" "+e[i])
            else:
                error+=e[i]
        results["server_health"]["reachable"] = False
        results["server_health"]["details"] = error
    return results

def set_env_vars():
    try:
        # Load the JSON file
        with open(CONFIG_FILE, 'r') as file:
            config = json.load(file)

        # Set each key-value pair as an environment variable
        for key, value in config.items():
            os.environ[key] = str(value)  # Convert value to string if not already

        print("Environment variables set successfully.")

    except FileNotFoundError:
        print(f"Configuration file '{CONFIG_FILE}' not found.")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")

def check_config():
    try:
        # Load the JSON file
        with open(CONFIG_FILE, 'r') as file:
            config = json.load(file)

        chirpstack_check = check_chirpstack_server_and_api(config["CHIRPSTACK_SERVER"], config["CHIRPSTACK_APIKEY"])

        if not(chirpstack_check["server_health"]["reachable"] and chirpstack_check["api_key_valid"]["valid"]):
            return False
        
        influxdb_check = check_influxdb_server_auth_and_resources(config["INFLUXDB_SERVER"], config["INFLUXDB_TOKEN"], config["INFLUXDB_ORG"], config["INFLUXDB_BUCKET"])
        if not(influxdb_check["server_health"]["reachable"] and influxdb_check["auth_valid"]["valid"] and influxdb_check["org_valid"]["valid"] and influxdb_check["bucket_valid"]["valid"]):
            return False
        
        rabbitmq_check = check_rabbitmq_server(config["MESSAGE_BROKER"])
        if not(rabbitmq_check["server_health"]["reachable"]):
            return False
        return True
        
    except FileNotFoundError:
        print(f"Configuration file '{CONFIG_FILE}' not found.")
        return False
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return False