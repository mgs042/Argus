import os
import grpc
import json
from chirpstack_api import api
from google.protobuf.json_format import MessageToJson
from datetime import datetime, timedelta
from google.protobuf.timestamp_pb2 import Timestamp

def get_tenant_list():
    # Get environment variables
    api_token = os.getenv('CHIRPSTACK_APIKEY')
    chirpstack_server = os.getenv('CHIRPSTACK_SERVER')
    auth_token = [("authorization", "Bearer %s" % api_token)]
    with grpc.insecure_channel(chirpstack_server) as channel:
         client = api.TenantServiceStub(channel)
         req = api.ListTenantsRequest()
         req.limit = 100 #mandatory if you want details
         resp = client.List(req, metadata=auth_token)
    return json.loads(MessageToJson(resp))['result']

