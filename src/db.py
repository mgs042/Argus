import sqlite3
import uuid
import bcrypt

class user_database:
    db_file = "user.db"
    def __init__(self):
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        self.initialize_user_db()

    def initialize_user_db(self):   
        # Create a table if it doesn't exist
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            mob TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            uid TEXT NOT NULL,
            UNIQUE(username)
        )
        """)
        self.conn.commit()

    def check_user_registered(self, username):
        self.cursor.execute("""
        SELECT COUNT(*) FROM user WHERE username = ?
        """, (username,))
        result = self.cursor.fetchone()[0]
        return result > 0
    
    def check_uid_registered(self, uid):
        self.cursor.execute("""
        SELECT COUNT(*) FROM user WHERE uid = ?
        """, (uid,))
        result = self.cursor.fetchone()[0]
        return result > 0
    
    def fetch_user(self, uid):
        self.cursor.execute("""
        SELECT name, username FROM user
        WHERE uid = ?
        """, (uid, ))
        result = self.cursor.fetchone()
        return result

    def register_user(self, name, email, mob, username, password):
        check = self.check_user_registered(username)
        if not check:
            try:
                unique_id = str(uuid.uuid4())
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                self.cursor.execute("""
                INSERT INTO user (name, email, mob, username, password, uid)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (name, email, mob, username, password_hash, unique_id))
                self.conn.commit()
                print("User Regisered")
            except sqlite3.Error as e:
                print(f"Error saving to DB: {e}")
        else:
            return "User Already Registered"
    
    def check_credentials(self, username, password):
        if self.check_user_registered(username):
            self.cursor.execute("""
            SELECT password, uid FROM user
            WHERE username = ?
            """, (username,))
            result = self.cursor.fetchone()
            stored_password_hash = result[0]
            return (bcrypt.checkpw(password.encode('utf-8'), stored_password_hash), result[1])
        else:
            return False
    
    # Destroyer method to close the connection
    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
            print("User Database connection closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class gateway_database:
    db_file = "storage/gateway.db"
    def __init__(self):
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        self.initialize_gateway_db()

    def initialize_gateway_db(self):   
        # Create a table if it doesn't exist
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS gateway (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            eui TEXT NOT NULL,
            address TEXT NOT NULL,
            sim_number TEXT,
            coordinates TEXT NOT NULL,
            uid TEXT NOT NULL,
            UNIQUE(name, eui)
        )
        """)
        self.conn.commit()
    
    # Fetch gateway_location from the database
    def fetch_gateway_location(self, eui):
        self.cursor.execute("""
        SELECT address FROM gateway
        WHERE eui = ?
        """, (eui,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    # Fetch gateway_name from the database
    def fetch_gateway_name(self, eui):
        self.cursor.execute("""
        SELECT name FROM gateway
        WHERE eui = ?
        """, (eui,))
        result = self.cursor.fetchone()
        return result[0] if result else "Unknown"
    
    def fetch_gateway_eui(self, uid):
        # Fetch gateway_eui from the database
        self.cursor.execute("""
        SELECT eui FROM gateway
        WHERE uid = ?
        """, (uid,))
        result = self.cursor.fetchone()
        return result[0] if result else "Unknown"
    
    def fetch_gateway_uid(self, eui):
        # Fetch uid from the database
        self.cursor.execute("""
        SELECT uid FROM gateway
        WHERE eui = ?
        """, (eui,))
        result = self.cursor.fetchone()
        return result[0] if result else "Unknown"
    
    def fetch_gateway_coordinates(self, eui):
        # Fetch coordinates from the database
        self.cursor.execute("""
        SELECT coordinates FROM gateway
        WHERE eui = ?
        """, (eui,))
        result = self.cursor.fetchone()
        return result[0] if result else "Unknown"
    
        
    # Check if Gateway is the database
    def check_gateway_registered(self, eui):
        self.cursor.execute("""
        SELECT name FROM gateway
        WHERE eui = ?
        """, (eui,))
        result = len(self.cursor.fetchall())
        return result
    
    
    #Set gateway address
    def set_gateway_address(self, eui, location):
        try:
            self.cursor.execute("""
            UPDATE gateway
            SET address = ?
            WHERE eui = ?
            """, (location, eui)) 
            self.conn.commit()  # Commit the changes to the database
        except sqlite3.Error as e:
            print(f"Error saving to DB: {e}")

    #Set gateway coordinates
    def set_gateway_coord(self, eui, coordinates):
        try:
            self.cursor.execute("""
            UPDATE gateway
            SET coordinates = ?
            WHERE eui = ?
            """, (coordinates, eui)) 
            self.conn.commit()  # Commit the changes to the database
        except sqlite3.Error as e:
            print(f"Error saving to DB: {e}")

    # Save gateway to the database
    def gateway_write(self, name, eui, address, sim_number, coordinates=''):
        check=self.check_gateway_registered(eui)
        if check== 0:
            try:
                unique_id = str(uuid.uuid4())
                self.cursor.execute("""
                INSERT OR IGNORE INTO gateway (name, eui, address, sim_number, coordinates, uid)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (name, eui, address, sim_number, coordinates, unique_id))
                self.conn.commit()
                return "Gateway Registered"
            except sqlite3.Error as e:
                print(f"Error saving to DB: {e}")
        else:
            return "Gateway Already Registered"

    def gateway_query(self):
        try:
            self.cursor.execute("""
            SELECT * FROM gateway
            """)
            result = self.cursor.fetchall()
            return result
        except sqlite3.Error as e:
            print(f"Error retrieving from DB: {e}")
        

    # Destroyer method to close the connection
    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
            print("Gateway Database connection closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()



class device_database:
    db_file = "storage/device.db"
    def __init__(self):
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        self.initialize_device_db()

    def initialize_device_db(self):
        
        # Create a table if it doesn't exist
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS device (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            eui TEXT NOT NULL,
            gw_id TEXT,
            dev_addr TEXT,
            uplink_interval INTEGER NOT NULL,
            uid TEXT NOT NULL,
            UNIQUE(name, eui)
        )
        """)
        self.conn.commit()
    
    
    # Check if Device is the database
    def check_device_registered(self, eui):
        self.cursor.execute("""
        SELECT name FROM device
        WHERE eui = ?
        """, (eui,))
        result = len(self.cursor.fetchall())
        return result
    
    # Check if Device address is the database
    def check_device_addr(self, eui):
        self.cursor.execute("""
        SELECT dev_addr FROM device
        WHERE eui = ?
        """, (eui,))
        result = self.cursor.fetchone()
        return result[0] != "Unknown"


    
    #Set Dev_addr
    def set_dev_addr(self, eui, dev_addr):
        try:
            self.cursor.execute("""
            UPDATE device
            SET dev_addr = ?
            WHERE eui = ?
            """, (dev_addr, eui)) 
            self.conn.commit()  # Commit the changes to the database
        except sqlite3.Error as e:
            print(f"Error saving to DB: {e}")

    # Check if Device gateway is the database
    def check_device_gw(self, eui):
        self.cursor.execute("""
        SELECT gw_id FROM device
        WHERE eui = ?
        """, (eui,))
        result = self.cursor.fetchone()
        return result[0] != "Unknown"


    
    #Set Dev gateway
    def set_dev_gw(self, eui, gw_id):
        try:
            self.cursor.execute("""
            UPDATE device
            SET gw_id = ?
            WHERE eui = ?
            """, (gw_id, eui)) 
            self.conn.commit()  # Commit the changes to the database
        except sqlite3.Error as e:
            print(f"Error saving to DB: {e}")

    #Get Device gateway
    def get_dev_gw(self, eui):
        try:
            self.cursor.execute("""
            SELECT gw_id from device
            WHERE eui = ?
            """, (eui,))
            result = self.cursor.fetchone()
            if result is not None:
                return result[0]
            else:
                return None
        except sqlite3.Error as e:
            print(f"Error retrieving from DB: {e}")

    def fetch_device_eui(self, uid):
        # Fetch device_eui from the database
        self.cursor.execute("""
        SELECT eui FROM device
        WHERE uid = ?
        """, (uid,))
        result = self.cursor.fetchone()
        return result[0] if result else "Unknown"
    
    # Save device to the database
    def device_write(self, name, eui, gw_id, dev_addr, uplink_interval):
        check=self.check_device_registered(eui)
        if check == 0:
            try:
                unique_id = str(uuid.uuid4())
                self.cursor.execute("""
                INSERT OR IGNORE INTO device (name, eui, gw_id, dev_addr, uplink_interval, uid)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (name, eui, gw_id, dev_addr, uplink_interval, unique_id))
                self.conn.commit()
                return "Device Registered"
            except sqlite3.Error as e:
                print(f"Error saving to DB: {e}")
        else:
            return "Device Already Registered"

    def device_query(self):
        try:
            self.cursor.execute("""
            SELECT * FROM device
            """)
            result = self.cursor.fetchall()
            return result
        except sqlite3.Error as e:
            print(f"Error retrieving from DB: {e}")
    
    def device_up_int_query(self):
        try:
            self.cursor.execute("""
            SELECT name, eui, uplink_interval FROM device
            """)
            result = self.cursor.fetchall()
            return result
        except sqlite3.Error as e:
            print(f"Error retrieving from DB: {e}")
        
    def gateway_up_int_query(self, gw_id):
        try:
            self.cursor.execute("""
            SELECT uplink_interval FROM device
            WHERE gw_id = ?                   
            """,(gw_id, ))
            result = self.cursor.fetchall()
            return result
        except sqlite3.Error as e:
            print(f"Error retrieving from DB: {e}")
    
    # Destroyer method to close the connection
    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
            print("Device Database connection closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

class alert_database:
    db_file = "storage/alert.db"
    def __init__(self):
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        self.initialize_alert_db()

    def initialize_alert_db(self):    
        # Create a table if it doesn't exist
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS alert (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            eui TEXT NOT NULL,
            issue TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL,
            uid TEXT NOT NULL
        )
        """)
        self.conn.commit()

    # Check if Alert is the database
    def check_alert_registered(self, eui, issue):
        self.cursor.execute("""
        SELECT name FROM alert
        WHERE eui = ? AND issue = ?
        """, (eui, issue,))
        result = self.cursor.fetchone()
        return result is not None

    # Check if Alert_uid is in the database
    def check_alert_uid_registered(self, uid):
        self.cursor.execute("""
        SELECT name FROM alert
        WHERE uid = ?
        """, (uid, ))
        result = self.cursor.fetchone()
        return result is not None

     # Save alert to the database
    def alert_write(self, name, eui, issue, message, severity):
        
        if not self.check_alert_registered(eui, issue):
            try:
                unique_id = str(uuid.uuid4())
                self.cursor.execute("""
                INSERT OR IGNORE INTO alert (name, eui, issue, message, severity, uid)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (name, eui, issue, message, severity, unique_id))
                self.conn.commit()
                return f"Alert Registered - {name} - {issue} - {message}"
            except sqlite3.Error as e:
                print(f"Error saving to DB: {e}")
        else:
            self.cursor.execute("""
            UPDATE alert
            SET message = ?
            WHERE eui = ? and issue = ?
            """, (message, eui, issue)) 
            self.conn.commit()
            return f"Alert Already Registered - {name} - {issue} - {message}"
    
    def query_alert(self, eui = None):
        if eui is not None:
            try:
                self.cursor.execute("""
                SELECT * FROM alert
                WHERE eui = ?
                """, (eui,))
                result = self.cursor.fetchall()
                return result
            except sqlite3.Error as e:
                print(f"Error retrieving from DB: {e}")
        else:
            try:
                self.cursor.execute("""
                SELECT * FROM alert
                """)
                result = self.cursor.fetchall()
                return result
            except sqlite3.Error as e:
                print(f"Error retrieving from DB: {e}")

    def get_alert_dev_eui(self, uid):
        self.cursor.execute("""
        SELECT eui FROM alert
        WHERE uid = ?
        """, (uid, ))
        result = self.cursor.fetchone()
        return result[0] if result else "Unknown"

    def get_dev_alerts(self, eui):
        self.cursor.execute("""
        SELECT * FROM alert
        WHERE eui = ?
        """, (eui, ))
        result = self.cursor.fetchall()
        return result


    def delete_alert(self, uid):
        try:
            self.cursor.execute("""
            DELETE FROM alert WHERE uid = ?
            """, (uid, ))
            self.conn.commit()
            
            if self.cursor.rowcount > 0:
                return "Alert Removed"
            else:
                return "Alert Not Found"
        except sqlite3.Error as e:
            print(f"Error removing from DB: {e}")
            return "Error occurred"

    def remove_alert(self, eui, issue):
        try:
            self.cursor.execute("""
            DELETE FROM alert WHERE eui = ? AND issue = ?
            """, (eui, issue))
            self.conn.commit()
            
            if self.cursor.rowcount > 0:
                return "Alert Removed"
            else:
                return "Alert Not Found"
        except sqlite3.Error as e:
            print(f"Error removing from DB: {e}")
            return "Error occurred"

        # Destroyer method to close the connection
    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
            print("Alert Database connection closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class gw_alert_database:
    db_file = "storage/gw_alert.db"
    def __init__(self):
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        self.initialize_alert_db()

    def initialize_alert_db(self):    
        # Create a table if it doesn't exist
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS alert (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            eui TEXT NOT NULL,
            issue TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL,
            uid TEXT NOT NULL
        )
        """)
        self.conn.commit()

    # Check if Alert is the database
    def check_alert_registered(self, eui, issue):
        self.cursor.execute("""
        SELECT name FROM alert
        WHERE eui = ? AND issue = ?
        """, (eui, issue,))
        result = self.cursor.fetchone()
        return result is not None

    # Check if Alert_uid is in the database
    def check_alert_uid_registered(self, uid):
        self.cursor.execute("""
        SELECT name FROM alert
        WHERE uid = ?
        """, (uid, ))
        result = self.cursor.fetchone()
        return result is not None

     # Save alert to the database
    def alert_write(self, name, eui, issue, message, severity):
        
        if not self.check_alert_registered(eui, issue):
            try:
                unique_id = str(uuid.uuid4())
                self.cursor.execute("""
                INSERT OR IGNORE INTO alert (name, eui, issue, message, severity, uid)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (name, eui, issue, message, severity, unique_id))
                self.conn.commit()
                return f"GW-Alert Registered - {name} - {issue} - {message}"
            except sqlite3.Error as e:
                print(f"Error saving to DB: {e}")
        else:
            self.cursor.execute("""
            UPDATE alert
            SET message = ?
            WHERE eui = ? and issue = ?
            """, (message, eui, issue)) 
            self.conn.commit()
            return f"GW-Alert Already Registered - {name} - {issue} - {message}"
    
    def query_alert(self, eui = None):
        if eui is not None:
            try:
                self.cursor.execute("""
                SELECT * FROM alert
                WHERE eui = ?
                """, (eui,))
                result = self.cursor.fetchall()
                return result
            except sqlite3.Error as e:
                print(f"Error retrieving from DB: {e}")
        else:
            try:
                self.cursor.execute("""
                SELECT * FROM alert
                """)
                result = self.cursor.fetchall()
                return result
            except sqlite3.Error as e:
                print(f"Error retrieving from DB: {e}")

    def get_alert_gw_eui(self, uid):
        self.cursor.execute("""
        SELECT eui FROM alert
        WHERE uid = ?
        """, (uid, ))
        result = self.cursor.fetchone()
        return result[0] if result else "Unknown"

    def get_gw_alerts(self, eui):
        self.cursor.execute("""
        SELECT * FROM alert
        WHERE eui = ?
        """, (eui, ))
        result = self.cursor.fetchall()
        return result


    def delete_alert(self, uid):
        try:
            self.cursor.execute("""
            DELETE FROM alert WHERE uid = ?
            """, (uid, ))
            self.conn.commit()
            
            if self.cursor.rowcount > 0:
                return "GW Alert Removed"
            else:
                return "GW Alert Not Found"
        except sqlite3.Error as e:
            print(f"Error removing from DB: {e}")
            return "Error occurred"

    def remove_alert(self, eui, issue):
        try:
            self.cursor.execute("""
            DELETE FROM alert WHERE eui = ? AND issue = ?
            """, (eui, issue))
            self.conn.commit()
            
            if self.cursor.rowcount > 0:
                return "GW Alert Removed"
            else:
                return "GW Alert Not Found"
        except sqlite3.Error as e:
            print(f"Error removing from DB: {e}")
            return "Error occurred"

        # Destroyer method to close the connection
    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
            print("GW Alert Database connection closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()