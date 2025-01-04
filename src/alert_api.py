from db import alert_database, device_database, gw_alert_database

def get_alert_status():
    alerts = []
    result = []
    with alert_database() as db:
        alerts += db.query_alert()
    with device_database() as db:
        for alert in alerts:
            result.append((alert[1], db.get_dev_gw(alert[2]), alert[3], alert[4], alert[5]))
    return result

def get_dev_alerts(device_eui):
    result = []
    with alert_database() as db:
        dev_alerts = db.get_dev_alerts(device_eui)
    with device_database() as db:
        for alert in dev_alerts:
            result.append((alert[1], db.get_dev_gw(alert[2]), alert[3], alert[4], alert[5]))
    return result

def get_gw_alert_status():
    alerts = []
    result = []
    with gw_alert_database() as db:
        alerts += db.query_alert()
    for alert in alerts:
            result.append((alert[1], alert[3], alert[4], alert[5]))
        
    return result

def get_gw_alerts(gateway_eui):
    result = []
    with gw_alert_database() as db:
        gw_alerts = db.get_gw_alerts(gateway_eui)
    for alert in gw_alerts:
        result.append((alert[1], alert[3], alert[4], alert[5]))
    return result