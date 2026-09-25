import time
import random
import urllib.request
import json

SERVER_URL = "http://127.0.0.1:8000/api/reading"

def generate_telemetry():
    """Simulates live ESP32 gas sensor telemetry (MQ-135, MQ-7, DHT11)"""
    co = round(random.uniform(0.6, 1.8), 2)
    co2 = round(random.uniform(410.0, 580.0), 1)
    pm25 = round(random.uniform(5.0, 22.0), 2)
    temp = round(random.uniform(27.0, 31.0), 1)
    hum = round(random.uniform(50.0, 68.0), 1)
    
    payload = {
        "co": co,
        "co2": co2,
        "pm25": pm25,
        "temp": temp,
        "hum": hum,
        "lat": 12.967959,
        "lon": 77.59506
    }
    return payload

def run_simulator(interval_seconds=3):
    print("📡 Starting EcoPulse ESP32-NODE-01 Sensor Simulator...")
    print(f"Target Server: {SERVER_URL}")
    while True:
        try:
            data = generate_telemetry()
            req = urllib.request.Request(
                SERVER_URL,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=4) as response:
                res = json.loads(response.read().decode())
                print(f"[+] Sent Reading -> AQI: {res.get('aqi')} ({res.get('category')}) | CO2: {data['co2']} ppm | CO: {data['co']} ppm | Temp: {data['temp']}C")
        except Exception as e:
            print(f"[!] Simulation send error: {e}")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    run_simulator()
