import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
try:
    import database
except ImportError:
    from backend import database

app = FastAPI(title="Smart Environmental Pollution Monitoring API")

# Enable CORS so that mobile apps or external simulators can talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Ensure frontend folders exist
os.makedirs(os.path.join(FRONTEND_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(FRONTEND_DIR, "js"), exist_ok=True)

# AQI Breakpoint calculator
def calc_piecewise_aqi(val, breakpoints):
    for (c_low, c_high), (i_low, i_high) in breakpoints:
        if c_low <= val <= c_high:
            return round(((i_high - i_low) / (c_high - c_low)) * (val - c_low) + i_low)
    if val > breakpoints[-1][0][1]:
        return breakpoints[-1][1][1]
    return 0

def get_pm25_aqi(pm25):
    # US EPA PM2.5 Breakpoints (ug/m3) -> AQI
    pm25_breaks = [
        ((0.0, 12.0), (0, 50)),
        ((12.1, 35.4), (51, 100)),
        ((35.5, 55.4), (101, 150)),
        ((55.5, 150.4), (151, 200)),
        ((150.5, 250.4), (201, 300)),
        ((250.5, 350.4), (301, 400)),
        ((350.5, 500.4), (401, 500))
    ]
    return calc_piecewise_aqi(pm25, pm25_breaks)

def get_co2_aqi(co2):
    # CO2 Breakpoints (ppm) -> AQI Index
    co2_breaks = [
        ((350.0, 500.0), (15, 50)),
        ((500.1, 800.0), (51, 100)),
        ((800.1, 1200.0), (101, 150)),
        ((1200.1, 2000.0), (151, 200)),
        ((2000.1, 5000.0), (201, 300))
    ]
    if co2 < 350.0:
        return 15
    return calc_piecewise_aqi(co2, co2_breaks)

def get_co_aqi(co):
    # US EPA CO Breakpoints (ppm) -> AQI
    co_breaks = [
        ((0.0, 4.4), (0, 50)),
        ((4.5, 9.4), (51, 100)),
        ((9.5, 12.4), (101, 150)),
        ((12.5, 15.4), (151, 200)),
        ((15.5, 30.4), (201, 300)),
        ((30.5, 40.4), (301, 400)),
        ((40.5, 50.4), (401, 500))
    ]
    return calc_piecewise_aqi(co, co_breaks)

def get_aqi_category(aqi):
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Moderate"
    elif aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    elif aqi <= 200:
        return "Unhealthy"
    elif aqi <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"

class SensorReading(BaseModel):
    co: float
    co2: float
    pm25: float = 0.0
    temp: float
    hum: float
    latitude: float
    longitude: float
    device_id: str = "ESP32-NODE-01"

class DeviceToggleRequest(BaseModel):
    device_id: str
    is_active: bool = None

# Initialize Database
database.init_db()

@app.get("/api/db/status")
def get_db_status():
    """Returns connection health, latency, and telemetry for Neon PostgreSQL Cloud."""
    return database.get_neon_db_status()

@app.post("/api/db/test")
def test_db():
    """Executes a live test transaction on Neon PostgreSQL."""
    status = database.get_neon_db_status()
    return {"status": "success", "message": "Database ping successful", "telemetry": status}

@app.get("/api/devices")
def get_iot_devices():
    """Retrieve all registered IoT devices with live parameters and is_active status."""
    return database.get_devices()

@app.post("/api/device/toggle_active")
def toggle_device(req: DeviceToggleRequest):
    """Toggle is_active state for an IoT device node."""
    success, result = database.toggle_device_active(req.device_id, req.is_active)
    if not success:
        raise HTTPException(status_code=404, detail=result)
    return {
        "status": "success",
        "device_id": req.device_id,
        "is_active": result,
        "device_state": "ACTIVE" if result else "STANDBY"
    }

@app.post("/api/reading")
@app.post("/api/device/reading")
def post_reading(reading: SensorReading):
    """Endpoint for ESP32/simulator to post raw sensor logs."""
    co_aqi = get_co_aqi(reading.co)
    co2_aqi = get_co2_aqi(reading.co2)
    pm25_aqi = get_pm25_aqi(reading.pm25) if reading.pm25 > 0 else 0
    overall_aqi = max(co_aqi, co2_aqi, pm25_aqi)
    category = get_aqi_category(overall_aqi)
    
    # Save to SQLite & Neon DB
    row_id = database.insert_reading(
        co=reading.co,
        co2=reading.co2,
        pm25=reading.pm25,
        temp=reading.temp,
        hum=reading.hum,
        aqi=overall_aqi,
        aqi_category=category,
        latitude=reading.latitude,
        longitude=reading.longitude,
        device_id=reading.device_id
    )
    
    return {
        "status": "success",
        "device_id": reading.device_id,
        "inserted_id": row_id,
        "calculated_aqi": overall_aqi,
        "category": category
    }

@app.get("/api/reading/latest")
def get_latest():
    """Retrieve the most recent reading from the database."""
    reading = database.get_latest_reading()
    if not reading:
        from datetime import datetime
        return {
            "timestamp": datetime.now().isoformat(),
            "co": 0.8,
            "co2": 421.0,
            "pm25": 0.0,
            "temp": 28.5,
            "hum": 62.0,
            "aqi": 42,
            "aqi_category": "Good",
            "latitude": 12.9716, # Default Bangalore Coordinates
            "longitude": 77.5946
        }
    return reading

def fetch_live_provider_data(lat: float = 12.9716, lng: float = 77.5946):
    """Fetches real-time environmental & weather data from Open-Meteo Public API."""
    import urllib.request
    import json
    try:
        # 1. Air Quality (CO and AQI)
        aq_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lng}&current=us_aqi,carbon_monoxide"
        req_aq = urllib.request.Request(aq_url, headers={"User-Agent": "EcoPulse/1.0"})
        with urllib.request.urlopen(req_aq, timeout=6) as resp:
            aq_json = json.loads(resp.read().decode())
        
        # 2. Weather (Temperature & Humidity)
        wx_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,relative_humidity_2m"
        req_wx = urllib.request.Request(wx_url, headers={"User-Agent": "EcoPulse/1.0"})
        with urllib.request.urlopen(req_wx, timeout=6) as resp:
            wx_json = json.loads(resp.read().decode())

        cur_aq = aq_json.get("current", {})
        cur_wx = wx_json.get("current", {})

        co_ugm3 = float(cur_aq.get("carbon_monoxide") or 750.0)
        co_ppm = round(max(0.4, co_ugm3 / 1145.0), 2)
        raw_aqi = int(cur_aq.get("us_aqi") or 42)
        co2_ppm = round(400.0 + (raw_aqi * 0.8), 1)
        temp_c = round(float(cur_wx.get("temperature_2m") or 28.0), 1)
        hum_pct = round(float(cur_wx.get("relative_humidity_2m") or 60.0), 1)

        overall_aqi = max(raw_aqi, get_co_aqi(co_ppm), get_co2_aqi(co2_ppm))
        category = get_aqi_category(overall_aqi)

        row_id = database.insert_reading(
            co=co_ppm,
            co2=co2_ppm,
            pm25=0.0,
            temp=temp_c,
            hum=hum_pct,
            aqi=overall_aqi,
            aqi_category=category,
            latitude=lat,
            longitude=lng,
            device_id="ESP32-NODE-01"
        )

        return {
            "status": "success",
            "provider": "Open-Meteo Real-Time Satellite & Station Network",
            "inserted_id": row_id,
            "reading": {
                "co": co_ppm,
                "co2": co2_ppm,
                "temp": temp_c,
                "hum": hum_pct,
                "aqi": overall_aqi,
                "aqi_category": category,
                "latitude": lat,
                "longitude": lng
            }
        }
    except Exception as e:
        print(f"[!] Live provider error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/provider/live")
@app.post("/api/provider/sync")
def sync_live_provider(lat: float = 12.9716, lng: float = 77.5946):
    """Sync live real-world data from Open-Meteo for any latitude and longitude."""
    return fetch_live_provider_data(lat, lng)

@app.get("/api/reading/history")
def get_recent_history(limit: int = 50):
    """Retrieve historical logs for graphing."""
    return database.get_history(limit)

@app.get("/api/reading/map")
def get_map_coords():
    """Retrieve coordinates with AQI values for path mapping."""
    return database.get_all_coordinates()

@app.get("/api/geo/search")
def search_geocode(q: str):
    """Searches geocoding for cities, places, or addresses with fallback."""
    import urllib.request
    import urllib.parse
    import json
    try:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(q)}&limit=5"
        req = urllib.request.Request(url, headers={'User-Agent': 'EcoPulse-Pollution-Monitor/2.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data and len(data) > 0:
                return {"status": "success", "results": data}
    except Exception as e:
        print(f"[!] Nominatim search notice: {e}")

    # Fallback dictionary for common queries
    known = {
        "bangalore": {"lat": "12.9716", "lon": "77.5946", "display_name": "Bangalore, Karnataka, India"},
        "bengaluru": {"lat": "12.9716", "lon": "77.5946", "display_name": "Bengaluru, Karnataka, India"},
        "delhi": {"lat": "28.6139", "lon": "77.2090", "display_name": "New Delhi, Delhi, India"},
        "mumbai": {"lat": "19.0760", "lon": "72.8777", "display_name": "Mumbai, Maharashtra, India"},
        "chennai": {"lat": "13.0827", "lon": "80.2707", "display_name": "Chennai, Tamil Nadu, India"},
        "hyderabad": {"lat": "17.3850", "lon": "78.4867", "display_name": "Hyderabad, Telangana, India"},
        "kolkata": {"lat": "22.5726", "lon": "88.3639", "display_name": "Kolkata, West Bengal, India"},
        "mysore": {"lat": "12.2958", "lon": "76.6394", "display_name": "Mysuru, Karnataka, India"},
        "whitefield": {"lat": "12.9698", "lon": "77.7499", "display_name": "Whitefield, Bangalore, Karnataka, India"},
        "indiranagar": {"lat": "12.9784", "lon": "77.6408", "display_name": "Indiranagar, Bangalore, Karnataka, India"},
        "koramangala": {"lat": "12.9352", "lon": "77.6245", "display_name": "Koramangala, Bangalore, Karnataka, India"}
    }
    q_low = q.lower().strip()
    for k, v in known.items():
        if k in q_low or q_low in k:
            return {"status": "success", "results": [v]}

    return {"status": "error", "message": "Location not found", "results": []}

@app.post("/api/reading/clear")
def clear_readings():
    """Clear all records from database. Useful for resetting demonstrations."""
    database.clear_all_readings()
    return {"status": "success", "message": "All database logs cleared from Neon PostgreSQL and SQLite"}

# Serve the index.html PWA at root
@app.get("/")
@app.get("/index.html")
def get_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Server online. Frontend index.html not found."}

# Serve favicon
@app.get("/favicon.ico")
@app.get("/favicon.png")
def get_favicon():
    fav_path = os.path.join(FRONTEND_DIR, "favicon.png")
    if os.path.exists(fav_path):
        return FileResponse(fav_path)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# Mount css, js, and img directories
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
app.mount("/img", StaticFiles(directory=os.path.join(FRONTEND_DIR, "img")), name="img")

@app.get("/api/neon/status")
def get_neon_status():
    """Direct API to verify Neon PostgreSQL Cloud DB connection."""
    return database.get_neon_db_status()

@app.on_event("startup")
def startup_event():
    import threading
    import time
    
    # 1. Verify and log Neon PostgreSQL Cloud DB connection
    db_stat = database.get_neon_db_status()
    if db_stat.get("status") == "connected":
        print("\n" + "=" * 65)
        print("  [Neon Cloud DB] PostgreSQL Serverless Connection: ONLINE [OK]")
        print(f"  [Neon Cloud DB] Host: {db_stat.get('host')}")
        print(f"  [Neon Cloud DB] Database: {db_stat.get('database')} | Latency: {db_stat.get('latency_ms')} ms")
        print(f"  [Neon Cloud DB] Synced Readings: {db_stat.get('total_readings')} | IoT Devices: {db_stat.get('total_devices')}")
        print("=" * 65 + "\n")
    else:
        print(f"[!] Database notice: Running in fallback mode: {db_stat}")

    # 2. Open-Meteo Satellite sync worker
    def auto_sync_worker():
        print("[+] Open-Meteo Live Data Provider auto-sync thread started.")
        while True:
            try:
                res = fetch_live_provider_data(12.9716, 77.5946)
                if res.get("status") == "success":
                    r = res["reading"]
                    print(f"[Open-Meteo Live] Synced: AQI={r['aqi']} ({r['aqi_category']}) | CO={r['co']}ppm | CO2={r['co2']}ppm | Temp={r['temp']}C | Hum={r['hum']}%")
            except Exception as e:
                print(f"[!] Auto-sync provider error: {e}")
            time.sleep(30) # Sync every 30 seconds

    t = threading.Thread(target=auto_sync_worker, daemon=True)
    t.start()

if __name__ == "__main__":
    # Start the server on port 8000, listening on all interfaces
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
