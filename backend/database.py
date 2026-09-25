import os
import time
import sqlite3
from datetime import datetime

# Neon PostgreSQL Database Connection URL
NEON_DB_URL = "postgresql://neondb_owner:npg_xdRPS7mJas0M@ep-soft-brook-b30hvtau-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pollution.db")

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

def get_neon_connection():
    if not HAS_PSYCOPG2:
        return None
    try:
        conn = psycopg2.connect(NEON_DB_URL, connect_timeout=5)
        return conn
    except Exception as e:
        print(f"[!] Neon DB Connection notice: {e}")
        return None

def get_sqlite_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes Neon PostgreSQL database and local SQLite fallback with all tables."""
    # 1. Initialize Neon PostgreSQL
    neon_conn = get_neon_connection()
    if neon_conn:
        try:
            cur = neon_conn.cursor()
            # Readings Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS readings (
                    id SERIAL PRIMARY KEY,
                    timestamp VARCHAR(50) NOT NULL,
                    co REAL NOT NULL,
                    co2 REAL NOT NULL,
                    pm25 REAL NOT NULL,
                    temp REAL NOT NULL,
                    hum REAL NOT NULL,
                    aqi INTEGER NOT NULL,
                    aqi_category VARCHAR(100) NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL
                );
            """)
            # IoT Devices Table with is_active flag
            cur.execute("""
                CREATE TABLE IF NOT EXISTS iot_devices (
                    device_id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    status VARCHAR(50) DEFAULT 'ACTIVE',
                    last_seen VARCHAR(50) NOT NULL,
                    co REAL DEFAULT 0.8,
                    co2 REAL DEFAULT 421.0,
                    temp REAL DEFAULT 28.5,
                    hum REAL DEFAULT 62.0,
                    aqi INTEGER DEFAULT 42,
                    aqi_category VARCHAR(50) DEFAULT 'Good',
                    battery_pct INTEGER DEFAULT 98,
                    location VARCHAR(100) DEFAULT 'Bangalore HQ Station'
                );
            """)
            # Seed default IoT devices if not present
            cur.execute("SELECT COUNT(*) FROM iot_devices;")
            if cur.fetchone()[0] == 0:
                now_str = datetime.now().isoformat()
                cur.execute("""
                    INSERT INTO iot_devices (device_id, name, is_active, status, last_seen, co, co2, temp, hum, aqi, aqi_category, battery_pct, location)
                    VALUES 
                    ('ESP32-NODE-01', 'ESP32 Stationary Environmental Station', TRUE, 'ONLINE', %s, 0.8, 421.0, 28.5, 62.0, 42, 'Good', 98, 'Station 1 - Central Bangalore'),
                    ('ESP32-NODE-02', 'ESP32 Mobile Rover / Drone Node', TRUE, 'ACTIVE', %s, 1.2, 465.0, 29.2, 58.0, 58, 'Moderate', 85, 'Rover 2 - Industrial Zone');
                """, (now_str, now_str))
            neon_conn.commit()
            neon_conn.close()
            print("[+] Neon PostgreSQL database initialized successfully with readings & iot_devices tables!")
        except Exception as e:
            print(f"[!] Failed to initialize Neon DB: {e}")
            if neon_conn: neon_conn.close()

    # 2. Initialize SQLite Fallback
    sq_conn = get_sqlite_connection()
    cur = sq_conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            co REAL NOT NULL,
            co2 REAL NOT NULL,
            pm25 REAL NOT NULL,
            temp REAL NOT NULL,
            hum REAL NOT NULL,
            aqi INTEGER NOT NULL,
            aqi_category TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS iot_devices (
            device_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            status TEXT DEFAULT 'ACTIVE',
            last_seen TEXT NOT NULL,
            co REAL DEFAULT 0.8,
            co2 REAL DEFAULT 421.0,
            temp REAL DEFAULT 28.5,
            hum REAL DEFAULT 62.0,
            aqi INTEGER DEFAULT 42,
            aqi_category TEXT DEFAULT 'Good',
            battery_pct INTEGER DEFAULT 98,
            location TEXT DEFAULT 'Bangalore HQ Station'
        )
    """)
    cur.execute("SELECT COUNT(*) FROM iot_devices;")
    if cur.fetchone()[0] == 0:
        now_str = datetime.now().isoformat()
        cur.execute("""
            INSERT INTO iot_devices (device_id, name, is_active, status, last_seen, co, co2, temp, hum, aqi, aqi_category, battery_pct, location)
            VALUES 
            ('ESP32-NODE-01', 'ESP32 Stationary Environmental Station', 1, 'ONLINE', ?, 0.8, 421.0, 28.5, 62.0, 42, 'Good', 98, 'Station 1 - Central Bangalore'),
            ('ESP32-NODE-02', 'ESP32 Mobile Rover / Drone Node', 1, 'ACTIVE', ?, 1.2, 465.0, 29.2, 58.0, 58, 'Moderate', 85, 'Rover 2 - Industrial Zone');
        """, (now_str, now_str))
    sq_conn.commit()
    sq_conn.close()

def get_neon_db_status():
    """Returns real-time connection telemetry for Neon PostgreSQL Cloud."""
    start_t = time.time()
    neon_conn = get_neon_connection()
    if neon_conn:
        try:
            cur = neon_conn.cursor()
            cur.execute("SELECT COUNT(*) FROM readings;")
            total_readings = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM iot_devices;")
            total_devices = cur.fetchone()[0]
            neon_conn.close()
            latency = round((time.time() - start_t) * 1000, 2)
            return {
                "status": "connected",
                "provider": "Neon PostgreSQL Serverless Cloud (AWS Singapore)",
                "database": "neondb",
                "host": "ep-soft-brook-b30hvtau-pooler.c-4.ap-southeast-1.aws.neon.tech",
                "latency_ms": latency,
                "total_readings": total_readings,
                "total_devices": total_devices,
                "driver": "psycopg2-binary (PostgreSQL 16+)",
                "ssl_mode": "require",
                "healthy": True
            }
        except Exception as e:
            if neon_conn: neon_conn.close()
            return {
                "status": "error",
                "error": str(e),
                "healthy": False,
                "fallback": "SQLite active"
            }
    
    # Fallback status
    try:
        sq_conn = get_sqlite_connection()
        cur = sq_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM readings;")
        sq_readings = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM iot_devices;")
        sq_devices = cur.fetchone()[0]
        sq_conn.close()
        return {
            "status": "fallback_sqlite",
            "provider": "Local SQLite Database Engine",
            "database": "pollution.db",
            "total_readings": sq_readings,
            "total_devices": sq_devices,
            "healthy": True
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "healthy": False}

def insert_reading(co, co2, pm25, temp, hum, aqi, aqi_category, latitude, longitude, device_id="ESP32-NODE-01"):
    """Inserts a new sensor reading into Neon PostgreSQL (and SQLite backup) and updates IoT device state."""
    timestamp = datetime.now().isoformat()
    row_id = 1

    # Try Neon PostgreSQL first
    neon_conn = get_neon_connection()
    if neon_conn:
        try:
            cur = neon_conn.cursor()
            cur.execute("""
                INSERT INTO readings (timestamp, co, co2, pm25, temp, hum, aqi, aqi_category, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (timestamp, co, co2, pm25, temp, hum, aqi, aqi_category, latitude, longitude))
            row_id = cur.fetchone()[0]
            
            # Update IoT device in Neon
            cur.execute("""
                UPDATE iot_devices 
                SET last_seen = %s, co = %s, co2 = %s, temp = %s, hum = %s, aqi = %s, aqi_category = %s, status = 'ONLINE'
                WHERE device_id = %s;
            """, (timestamp, co, co2, temp, hum, aqi, aqi_category, device_id))
            
            neon_conn.commit()
            neon_conn.close()
        except Exception as e:
            print(f"[!] Neon insert error: {e}")
            if neon_conn: neon_conn.close()

    # Save to SQLite local backup as well
    try:
        sq_conn = get_sqlite_connection()
        cur = sq_conn.cursor()
        cur.execute("""
            INSERT INTO readings (timestamp, co, co2, pm25, temp, hum, aqi, aqi_category, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, co, co2, pm25, temp, hum, aqi, aqi_category, latitude, longitude))
        sq_id = cur.lastrowid
        
        cur.execute("""
            UPDATE iot_devices 
            SET last_seen = ?, co = ?, co2 = ?, temp = ?, hum = ?, aqi = ?, aqi_category = ?, status = 'ONLINE'
            WHERE device_id = ?
        """, (timestamp, co, co2, temp, hum, aqi, aqi_category, device_id))
        
        sq_conn.commit()
        sq_conn.close()
        if not neon_conn:
            row_id = sq_id
    except Exception as e:
        print(f"[!] SQLite insert error: {e}")

    return row_id

def get_latest_reading():
    """Retrieves the most recent sensor reading from Neon PostgreSQL or SQLite fallback."""
    neon_conn = get_neon_connection()
    if neon_conn:
        try:
            cur = neon_conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            neon_conn.close()
            if row:
                return dict(row)
        except Exception as e:
            print(f"[!] Neon query error: {e}")
            if neon_conn: neon_conn.close()

    # Fallback SQLite query
    sq_conn = get_sqlite_connection()
    cur = sq_conn.cursor()
    cur.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    sq_conn.close()
    if row:
        return dict(row)
    return None

def get_devices():
    """Retrieves all registered IoT devices with live parameters and is_active flag."""
    neon_conn = get_neon_connection()
    if neon_conn:
        try:
            cur = neon_conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM iot_devices ORDER BY device_id ASC")
            rows = cur.fetchall()
            neon_conn.close()
            if rows:
                return [dict(r) for r in rows]
        except Exception as e:
            print(f"[!] Neon devices query error: {e}")
            if neon_conn: neon_conn.close()

    # Fallback SQLite
    sq_conn = get_sqlite_connection()
    cur = sq_conn.cursor()
    cur.execute("SELECT * FROM iot_devices ORDER BY device_id ASC")
    rows = cur.fetchall()
    sq_conn.close()
    devices = []
    for r in rows:
        d = dict(r)
        d['is_active'] = bool(d.get('is_active', 1))
        devices.append(d)
    return devices

def toggle_device_active(device_id: str, is_active: bool = None):
    """Toggles or sets the is_active status of an IoT device."""
    devices = get_devices()
    target = next((d for d in devices if d['device_id'] == device_id), None)
    if not target:
        return False, f"Device {device_id} not found"

    new_state = (not target['is_active']) if is_active is None else is_active
    status_str = "ACTIVE" if new_state else "STANDBY"

    # 1. Update Neon PostgreSQL
    neon_conn = get_neon_connection()
    if neon_conn:
        try:
            cur = neon_conn.cursor()
            cur.execute("""
                UPDATE iot_devices 
                SET is_active = %s, status = %s
                WHERE device_id = %s
            """, (new_state, status_str, device_id))
            neon_conn.commit()
            neon_conn.close()
        except Exception as e:
            print(f"[!] Neon toggle device error: {e}")
            if neon_conn: neon_conn.close()

    # 2. Update SQLite
    sq_conn = get_sqlite_connection()
    cur = sq_conn.cursor()
    cur.execute("""
        UPDATE iot_devices 
        SET is_active = ?, status = ?
        WHERE device_id = ?
    """, (1 if new_state else 0, status_str, device_id))
    sq_conn.commit()
    sq_conn.close()

    return True, new_state

def get_history(limit=50):
    """Retrieves recent sensor reading history with normalized keys."""
    raw_rows = []
    neon_conn = get_neon_connection()
    if neon_conn:
        try:
            cur = neon_conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM readings ORDER BY id DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
            neon_conn.close()
            raw_rows = [dict(r) for r in reversed(rows)]
        except Exception as e:
            print(f"[!] Neon history query error: {e}")
            if neon_conn: neon_conn.close()

    if not raw_rows:
        # Fallback SQLite
        try:
            sq_conn = get_sqlite_connection()
            cur = sq_conn.cursor()
            cur.execute("SELECT * FROM readings ORDER BY id DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            sq_conn.close()
            raw_rows = [dict(r) for r in reversed(rows)]
        except Exception as e:
            print(f"[!] SQLite history query error: {e}")

    # Normalize fields so all clients (Web + APK) get standard keys
    cleaned = []
    for r in raw_rows:
        item = dict(r)
        temp_val = float(item.get("temp", item.get("temperature", 28.5)))
        hum_val = float(item.get("hum", item.get("humidity", 60.0)))
        item["temp"] = temp_val
        item["temperature"] = temp_val
        item["hum"] = hum_val
        item["humidity"] = hum_val
        cleaned.append(item)
    return cleaned

def get_all_coordinates():
    """Retrieves all coordinates with their AQI levels for mapping."""
    neon_conn = get_neon_connection()
    if neon_conn:
        try:
            cur = neon_conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT timestamp, latitude, longitude, aqi, aqi_category FROM readings ORDER BY id ASC")
            rows = cur.fetchall()
            neon_conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"[!] Neon coords query error: {e}")
            if neon_conn: neon_conn.close()

    # Fallback SQLite
    sq_conn = get_sqlite_connection()
    cur = sq_conn.cursor()
    cur.execute("SELECT timestamp, latitude, longitude, aqi, aqi_category FROM readings ORDER BY id ASC")
    rows = cur.fetchall()
    sq_conn.close()
    return [dict(r) for r in rows]

def clear_all_readings():
    """Clears all readings safely from Neon PostgreSQL and SQLite."""
    neon_conn = get_neon_connection()
    if neon_conn:
        try:
            cur = neon_conn.cursor()
            cur.execute("DELETE FROM readings;")
            neon_conn.commit()
            neon_conn.close()
        except Exception as e:
            print(f"[!] Neon clear error: {e}")
            if neon_conn: neon_conn.close()

    sq_conn = get_sqlite_connection()
    cur = sq_conn.cursor()
    cur.execute("DELETE FROM readings;")
    sq_conn.commit()
    sq_conn.close()
    return True

if __name__ == "__main__":
    init_db()
    print("DB Status:", get_neon_db_status())
    print("Devices:", get_devices())

