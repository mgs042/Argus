import os
import grpc
import json
from chirpstack_api import api
from google.protobuf.json_format import MessageToJson
from datetime import datetime, timedelta
from google.protobuf.timestamp_pb2 import Timestamp
from tenant_api import get_tenant_list

application_count = 0
tenant_count = 0

def get_application_list():

    global tenant_count, application_count
    application_count = 0
    tenant_count = 0
    # Get environment variables
    api_token = os.getenv('CHIRPSTACK_APIKEY')
    chirpstack_server = os.getenv('CHIRPSTACK_SERVER')
    auth_token = [("authorization", "Bearer %s" % api_token)]
    application_list=[]
    with grpc.insecure_channel(chirpstack_server) as channel:
        tenant_list=get_tenant_list()
        tenant_count += len(tenant_list)
        for i in range(len(tenant_list)):
                client = api.ApplicationServiceStub(channel)
                req = api.ListApplicationsRequest()
                req.limit = 100 #mandatory if you want details
                req.tenant_id = tenant_list[i]['id']
                resp = client.List(req, metadata=auth_token)
                resp_json = json.loads(MessageToJson(resp))
                application_count += resp_json['totalCount']
                application_list += resp_json['result']
    return application_list

def get_tenant_count():
     return tenant_count

def get_app_count():
     return application_count