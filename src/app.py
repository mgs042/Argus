import os
from config import set_env_vars, check_chirpstack_server_and_api, check_influxdb_server_auth_and_resources, check_rabbitmq_server, check_config, set_config_file
set_env_vars()
from flask import Flask, request, Response, render_template, jsonify, redirect, url_for, make_response, flash
from flask_cors import CORS
from db import gateway_database, device_database, alert_database, gw_alert_database, user_database
with alert_database() as db:
    db.clear_alert_table()
with gw_alert_database() as db:
    db.clear_alert_table()
from application_api import get_tenant_count, get_app_count
from gateway_api import get_gateway_details, get_gateway_metrics, get_gateways_status
from device_api import get_dev_details, get_dev_status, get_device_metrics
from alert_api import get_alert_status, get_dev_alerts, get_gw_alert_status, get_gw_alerts
from celery_tasks import celery_init_app, update_influx, configure_celery_beat
from location import rev_geocode
from flask_jwt_extended import (JWTManager, jwt_required, get_jwt_identity,
                                create_access_token, create_refresh_token, 
                                set_access_cookies, set_refresh_cookies, 
                                unset_jwt_cookies,unset_access_cookies)

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)  # Enable CORS for all routes


# Configure application to store JWTs in cookies
app.config['JWT_TOKEN_LOCATION'] = ['cookies']

# Only allow JWT cookies to be sent over https. In production, this should likely be True
app.config['JWT_COOKIE_SECURE'] = False

# Set the cookie paths, so that you are only sending your access token
# cookie to the access endpoints, and only sending your refresh token
# to the refresh endpoint. Technically this is optional, but it is in
# your best interest to not send additional cookies in the request if
# they aren't needed.
# app.config['JWT_ACCESS_COOKIE_PATH'] = '/api/'
app.config['JWT_REFRESH_COOKIE_PATH'] = '/token/refresh'

app.config['JWT_COOKIE_CSRF_PROTECT'] = True
app.config['JWT_CSRF_CHECK_FORM'] = True

app.config["JWT_SECRET_KEY"] = str(os.urandom(32).hex())
jwt = JWTManager(app)

app.config.from_mapping(
    CELERY=dict(
        broker_url=f"amqp://guest:guest@{os.getenv('MESSAGE_BROKER')}//",
        result_backend=None,
        task_ignore_result=True,
    ),
)
celery_app = celery_init_app(app)

configure_celery_beat(celery_app)

@app.route('/', methods=['GET'])
def index():
    return render_template('login.html')

@app.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
        else:
            name, username = db.fetch_user(uid)
    if check_config():
        return render_template("dashboard.html", tenant_count=get_tenant_count(), app_count=get_app_count(), name=name, username=username)
    else:
        flash("Configuration Check Failed -- One or more of the required dependencies have not been met")
        return redirect(url_for('config_details'))
    
@app.route('/device_alerts', methods=['GET'])
@jwt_required()
def device_status():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
    return jsonify(get_alert_status())

@app.route('/gateway_alerts', methods=['GET'])
@jwt_required()
def gateway_alerts():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
    return jsonify(get_gw_alert_status())
    
@app.route('/status_data', methods=['GET'])
@jwt_required()
def status_data():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
    return {
        'gateways': get_gateways_status(),
        'devices': get_dev_status()
    }


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    with user_database() as db:
        check, uid = db.check_credentials(username, password)
        if check:
            # Create the tokens we will be sending back to the user
            access_token = create_access_token(identity=uid)
            refresh_token = create_refresh_token(identity=uid)
            resp = redirect(url_for('dashboard'))
            set_access_cookies(resp, access_token)
            set_refresh_cookies(resp, refresh_token)
            return resp     
        else:
            flash("Bad Credentials -- Username or Password is Incorrect")
            return redirect(url_for('index'))

        
@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
    resp = redirect(url_for('index'))
    unset_jwt_cookies(resp)
    return resp, 200


@app.route('/token/refresh', methods=['GET'])
@jwt_required(refresh=True)
def refresh():
    # Refreshing expired Access token
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
    access_token = create_access_token(identity=str(uid))
    resp = make_response(redirect(url_for('dashboard')))
    set_access_cookies(resp, access_token)
    return resp

@app.route('/user_registration', methods=['GET', 'POST'])
@jwt_required()
def user_register():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
        else:
            name, username = db.fetch_user(uid)
    if request.method == 'GET':
        return render_template('user_reg.html', name=name, username=username)
    elif request.method == 'POST':
        u_name = request.form.get('name')
        u_email = request.form.get('email') or "Unknown"
        u_mob = request.form.get('mob') or "Unknown"
        u_username = request.form.get('username')
        u_password = request.form.get('password')
        u_re_password = request.form.get('re-password')
        if u_password != u_re_password:
            flash("Passwords do not match")
            return redirect(url_for('user_register'))

        else:
            with user_database() as db:
                result = db.register_user(u_name, u_email, u_mob, u_username, u_password)
            if result == "User Already Registered":
                flash("Username already exists -- Please select a unique username")
                return redirect(url_for('user_register'))

            else:
                return redirect(url_for('index'))
            

@app.route('/account_settings', methods=['GET', 'POST'])
@jwt_required()
def account_settings():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
        else:
            name, username = db.fetch_user(uid)
        user = db.fetch_user_details(uid)
    if request.method == 'GET':
        return render_template('account_settings.html', name=name, username=username, user = user)
    elif request.method == 'POST':
        u_name = request.form.get('name')
        u_email = request.form.get('email') or "Unknown"
        u_mob = request.form.get('mob') or "Unknown"
        u_username = request.form.get('username')
        with user_database() as db:
            if u_username != username and db.check_user_registered(u_username):
                flash("Username already exists -- Please select a unique username")
                return redirect(url_for('account_settings'))
            else:
                db.update_user(u_name, u_email, u_mob, u_username, uid)
        return redirect(url_for('account_settings'))
                    


@app.route('/config_details', methods=['GET', 'POST'])
@jwt_required()
def config_details():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
        else:
            name, username = db.fetch_user(uid)
    if request.method == 'POST':
        chirpstack_server = influxdb_server = rabbitmq_server = None
        if request.form.get('chirpstack-ip') != None and request.form.get('chirpstack-port') != None:
            chirpstack_server = request.form.get('chirpstack-ip') + ':' + request.form.get('chirpstack-port')
        if request.form.get('influxdb-ip') != None and request.form.get('influxdb-port') != None:
            influxdb_server = request.form.get('influxdb-ip') + ':' + request.form.get('influxdb-port')
        if request.form.get('rabbitmq-ip') != None and request.form.get('rabbitmq-port') != None:
            rabbitmq_server = request.form.get('rabbitmq-ip') + ':' + request.form.get('rabbitmq-port')
        config_var = {
                    "CHIRPSTACK_APIKEY": request.form.get('chirpstack-api'),
                    "CHIRPSTACK_SERVER": chirpstack_server,
                    "MESSAGE_BROKER": "",
                    "INFLUXDB_SERVER": "",
                    "INFLUXDB_TOKEN": "",
                    "INFLUXDB_ORG": "",
                    "INFLUXDB_BUCKET": ""
                }

        
        set_config_file(config_var=config_var)

    chirpstack_status = check_chirpstack_server_and_api(os.getenv("CHIRPSTACK_SERVER"), os.getenv("CHIRPSTACK_APIKEY"))
    influxdb_status = check_influxdb_server_auth_and_resources(os.getenv("INFLUXDB_SERVER"), os.getenv("INFLUXDB_TOKEN"), os.getenv("INFLUXDB_ORG"), os.getenv("INFLUXDB_BUCKET"))
    rabbitmq_status = check_rabbitmq_server(os.getenv("MESSAGE_BROKER"))
    return render_template("config_details.html", chirpstack_status=chirpstack_status, influxdb_status=influxdb_status, rabbitmq_status=rabbitmq_status, name=name, username=username)


@app.route('/gateway_registration', methods=['GET', 'POST'])
@jwt_required()
def gateway_register():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
        else:
            name, username = db.fetch_user(uid)
    if request.method == 'POST':
        g_name = request.form.get('name')
        g_id = request.form.get('eui')
        g_address = request.form.get('address')
        g_number = request.form.get('number')
        with gateway_database() as db:
            result=db.gateway_write(g_name, g_id, g_address, g_number)
        return redirect(url_for('gateways'))

        
    return render_template("gateway_reg.html", name=name, username=username)

@app.route('/device_registration', methods=['GET', 'POST'])
@jwt_required()
def dev_register():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
        else:
            name, username = db.fetch_user(uid)
    if request.method == 'POST':
        d_name = request.form.get('name')
        d_id = request.form.get('eui')
        d_gw = request.form.get('dev_gw') or "Unknown"
        d_addr = request.form.get('addr') or "Unknown"
        d_up_int = request.form.get('dev_up') or 60
        with device_database() as db:
            result=db.device_write(d_name, d_id, d_gw, d_addr, d_up_int)
        
        return redirect(url_for('devices'))
        
    return render_template("device_reg.html", name=name, username=username)

@app.route('/gateways', methods=['GET'])
@jwt_required()
def gateways():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
        else:
            name, username = db.fetch_user(uid)
    return render_template("gateways_list.html", name=name, username=username)

@app.route('/devices', methods=['GET'])
@jwt_required()
def devices():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
        else:
            name, username = db.fetch_user(uid)
    return render_template("devices_list.html", name=name, username=username)

@app.route('/gateway', methods=['GET'])
@jwt_required()
def gateway():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
        else:
            name, username = db.fetch_user(uid)
    if check_config():
        # Get the 'id' parameter from the query string
        gateway_uid = request.args.get('uid')
        alert_uid = request.args.get('alert_uid')
        if alert_uid is not None:
            with gw_alert_database() as db:
                gateway_id = db.get_alert_gw_eui(alert_uid)
            with gateway_database() as db:
                gateway_uid = db.fetch_gateway_uid(gateway_id)
        elif gateway_uid is not None:
            with gateway_database() as db:
                gateway_id = db.fetch_gateway_eui(gateway_uid)
        if gateway_id:
            with gateway_database() as db:
                check = db.check_gateway_registered(gateway_id)
            if check==0:
                return "Unknown Gateway"
            else:
                gateway_details = get_gateway_details(gateway_id)
                gateway_alerts = get_gw_alerts(gateway_id)
                return render_template("gateway_details.html", gateway=gateway_details, uid=gateway_uid, gw_alerts = gateway_alerts, name=name, username=username)
        
        else:
            # If no 'id' is passed, return a 400 error or some default message
            return 'No gateway ID provided', 400
    else:
        flash("Configuration Check Failed -- One or more of the required dependencies have not been met")
        return redirect(url_for('config_details'))

    
@app.route('/device', methods=['GET'])
@jwt_required()
def device():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
        else:
            name, username = db.fetch_user(uid)
    if check_config():
        # Get the 'uid' parameter from the query string
        device_uid = request.args.get('uid')
        alert_uid = request.args.get('alert_uid')
        if alert_uid is not None:
            with alert_database() as db:
                device_eui = db.get_alert_dev_eui(alert_uid)
            with device_database() as db:
                device_uid = db.fetch_device_uid(device_eui)
        elif device_uid is not None:
            with device_database() as db:
                device_eui = db.fetch_device_eui(device_uid)
        if device_eui:
            with device_database() as db:
                check = db.check_device_registered(device_eui)
            if check==0:
                return "Unknown Device"
            else:
                device_details = get_dev_details(device_eui)
                device_alerts = get_dev_alerts(device_eui)
                return render_template("device_details.html", device=device_details, uid=device_uid, dev_alerts=device_alerts, name=name, username=username)
        
        else:
            # If no 'id' is passed, return a 400 error or some default message
            return 'No device ID provided', 400
    else:
        flash("Configuration Check Failed -- One or more of the required dependencies have not been met")
        return redirect(url_for('config_details'))

    
@app.route('/gateway_metrics', methods=['GET'])
@jwt_required()
def gateway_metrics():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
    # Get the 'uid' parameter from the query string
    gateway_uid = request.args.get('uid')
    with gateway_database() as db:
        gateway_id = db.fetch_gateway_eui(gateway_uid)
    return get_gateway_metrics(gateway_id)

@app.route('/device_metrics', methods=['GET'])
@jwt_required()
def device_metrics():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
    # Get the 'uid' parameter from the query string
    device_uid = request.args.get('uid')
    with device_database() as db:
        device_id = db.fetch_device_eui(device_uid)
    return get_device_metrics(device_id)

@app.route('/gateway_data', methods=["GET"])
@jwt_required()
def gateway_data():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
    with gateway_database() as db:
        rows=db.gateway_query()
    return jsonify(rows)

@app.route('/device_data', methods=["GET"])
@jwt_required()
def device_data():
    uid = get_jwt_identity()
    with user_database() as db:
        if not db.check_uid_registered(uid):
            return redirect(url_for('index'))
    with device_database() as db:
        rows=db.device_query()
    return jsonify(rows)       


@app.route('/data', methods=['POST'])
def data():
    event_type = request.args.get('event')
    if event_type == 'up':
        #Recieve and process JSON data
        data = request.get_json()
        device_name = data.get('deviceInfo', {}).get('deviceName', 'Unknown')
        device_id = data.get('deviceInfo', {}).get('devEui', 'Unknown')
        device_addr = data.get('devAddr', 'Unknown')
        gateway_id = data.get('rxInfo', [{}])[0].get('gatewayId', 'Unknown')
        rssi = data.get('rxInfo', [{}])[0].get('rssi', 0)
        snr = data.get('rxInfo', [{}])[0].get('snr', 0)
        f_cnt = data.get('fCnt', -1)
        coordinates = data.get('rxInfo', [{}])[0].get('location', {})
        # Metrics data
        metrics_data = {
            'device_name': device_name,
            'device_id': device_id,
            'gateway_id': gateway_id,
            'rssi': rssi,
            'snr': snr,
            'f_cnt': f_cnt
        }
        
        # Update device metrics
        try:   
            update_influx.apply_async(args=[metrics_data, coordinates, device_addr])
            
        except Exception as e:
            print(f"Error updating metrics: {e}")
            return '', 500  # Internal Server Error
    elif event_type == 'join':
        #Recieve and process JSON data
        data = request.get_json()
        device_name = data.get('deviceInfo', {}).get('deviceName', 'Unknown')
        device_id = data.get('deviceInfo', {}).get('devEui', 'Unknown')
        device_addr = data.get('devAddr', 'Unknown')
        with device_database() as db:
            if db.check_device_registered(device_id):
                with alert_database() as db2:
                    print(db2.alert_write(device_name, device_id, "Join Request Replay", f"{device_name} has already joined before", 'critical'))
            else:
                db.device_write(device_name, device_id, "Unknown", device_addr, 60)
    elif event_type == 'status':
        #Recieve and process JSON data
        data = request.get_json()
        device_name = data.get('deviceInfo', {}).get('deviceName', 'Unknown')
        device_id = data.get('deviceInfo', {}).get('devEui', 'Unknown')
        margin = data.get('margin', 'Unknown')
        battery_level_unavailable = data.get('batteryLevelUnavailable', True)
        battery_status = data.get('batteryLevel', 'Unknown')
        if margin > 20:
            with alert_database() as db:
                print(db.alert_write(device_name, device_id, "High Link Margin", f'{device_name} has a high margin value of {margin}', 'low'))
        elif margin < 5:
            with alert_database() as db:
                print(db.alert_write(device_name, device_id, "Low Link Margin", f'{device_name} has a low margin value of {margin}', 'critical'))
        
        if (not battery_level_unavailable) and battery_status < 10:
            with alert_database() as db:
                print(db.alert_write(device_name, device_id, "Low Battery", f'{device_name} has a low battery level of {battery_status}', 'critical'))
    elif event_type == 'log':
         #Recieve and process JSON data
        data = request.get_json()
        device_name = data.get('deviceInfo', {}).get('deviceName', 'Unknown')
        device_id = data.get('deviceInfo', {}).get('devEui', 'Unknown')
        level = data.get('level', '')
        code = data.get('code', '')
        description = data.get('description', '')

        match level:
            case 'INFO':
                severity = 'low'
            case 'WARNING':
                severity = 'high'
            case 'ERROR':
                severity = 'critical'

        match code:
            case 'DOWNLINK_PAYLOAD_SIZE':
                issue = 'Downlink Payload Size Error'
            case 'UPLINK_CODEC':
                issue = 'Uplink Codec Error'
            case 'DOWNLINK_CODEC':
                issue = 'Downlink Codec Error'
            case 'OTAA':
                issue = 'OTAA Error'
            case 'UPLINK_F_CNT_RESET':
                issue = 'Uplink Frame-counter Reset'
            case 'UPLINK_MIC':
                issue = 'Uplink MIC Error'
            case 'UPLINK_F_CNT_RETRANSMISSION':
                issue = 'Uplink Frame-counter Retransmission'
            case 'DOWNLINK_GATEWAY':
                issue = 'Downlink Gateway Error'
            case 'RELAY_NEW_END_DEVICE':
                issue = 'Relay the Device'
            case 'EXPIRED':
                issue = 'Downlink Expired'
            case _:
                issue = 'Unidentified Log Event'
                severity = 'low'
        
        match description:
            case 'TOO_LATE':
                description = 'Packet is too late for Downlink to be sent'
            case 'TOO_EARLY':
                description = 'Downlink timestamp is too much in advance'
            case 'COLLISION_PACKET':
                description = 'Collides with another packet in the same timeframe'
            case 'COLLISION_BEACON':
                description = 'Collides with a beacon in the same timeframe'
            case 'TX_FREQ':
                description = 'Downlink frequency not supported by gateway'
            case 'TX_POWER':
                description = 'Downlink power not supported by gateway'
            case 'GPS_UNLOCKED':
                description = 'GPS unreliable and its timestamp cannot be used'
            case 'QUEUE_FULL':
                description = 'Too many pending Downlinks, queue is full'
            case 'INTERNAL_ERROR':
                description = 'Internal Error has occured'
            case 'DUTY_CYCLE_OVERFLOW':
                description = 'Transmission exceeds regulatory airtime limits'
            case _:
                if description == '':
                    description = 'Unknown'

        with alert_database() as db:
            print(db.alert_write(device_id, device_name, issue, description, severity))
    elif event_type == 'location':
        #Recieve and process JSON data
        data = request.get_json()
        device_id = data.get('deviceInfo', {}).get('devEui', 'Unknown')
        location = data.get('location', {})
        if location != {}:
            with device_database() as db:
                gateway_id = db.check_device_gw(device_id)
            with gateway_database() as db:
                gateway_location = db.fetch_gateway_location(gateway_id)
                gateway_name = db.fetch_gateway_name(gateway_id)
                try:
                    lat, long, alt = str(db.fetch_gateway_coordinates).split(',')
                except:
                    lat = long = alt = ''
            if lat == '' and long == '' and alt == '':
                    with gateway_database() as db:
                        db.set_gateway_coord(gateway_id, f'{lat},{long},{alt}')
            elif location['latitude'] != lat or location['longitude'] != long or location['altitude'] != alt:
                with gateway_database() as db:
                    db.set_gateway_coord(gateway_id, f'{lat},{long},{alt}')
                with gw_alert_database() as db:
                    print(db.alert_write(gateway_name, gateway_id, 'Gateway Location Changed', f'Location of {gateway_name} has changed by ({lat-location['latitude']}, {long-location['longitude']}, {alt-location['altitude']})', 'critical'))
            if gateway_location is None:
                try:
                    gateway_location = rev_geocode(location['latitude'], location['longitude'], metrics_data.get(gateway_id))
                    with gateway_database() as db:
                        db.set_gateway_address(gateway_id, gateway_location)
                except KeyError as e:
                    print(f"KeyError encountered: {e}")



    return '', 204  # No Content

@app.route('/delete_alert', methods=['GET'])
def delete_alert():
    uid = request.args.get('uid')
    with alert_database() as db:
        if db.check_alert_uid_registered(uid):
            db.delete_alert(uid)
    with gw_alert_database() as db:
        if db.check_alert_uid_registered(uid):
            db.delete_alert(uid)
    return redirect(url_for('dashboard'))


@jwt.unauthorized_loader
def unauthorized_callback(callback):
    # No auth header
    return redirect(url_for('index'))

@jwt.invalid_token_loader
def invalid_token_callback(callback):
    # Invalid Fresh/Non-Fresh Access token in auth header
    resp = make_response(redirect(url_for('index')))
    unset_jwt_cookies(resp)
    return resp, 302

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    # Expired auth header
    resp = make_response(redirect(url_for('refresh')))
    unset_access_cookies(resp)
    return resp, 302

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error-404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error-500.html'), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
