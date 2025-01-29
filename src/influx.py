from influxdb_client import InfluxDBClient
import os

def get_influxdb_client():
    try:
        influxdb_url = f"http://{os.getenv('INFLUXDB_SERVER')}"
        influxdb_token = os.getenv('INFLUXDB_TOKEN')
        influxdb_org = os.getenv('INFLUXDB_ORG')
        influxdb_bucket = os.getenv('INFLUXDB_BUCKET')

        if not influxdb_url or not influxdb_token or not influxdb_org or not influxdb_bucket:
            raise ValueError("Missing required InfluxDB environment variables.")

        client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org, timeout=30000)
        return client, influxdb_bucket, influxdb_org
    except Exception as e:
        print(f"Error connecting to InfluxDB: {e}")
        raise
