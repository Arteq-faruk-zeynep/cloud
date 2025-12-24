from fastapi import FastAPI, HTTPException, Depends
import psycopg2
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional
from fastapi.responses import FileResponse
import paho.mqtt.client as mqtt
import json
import time

app = FastAPI()

# --- JWT VE GÜVENLİK ---
SECRET_KEY = "zeynep_iot_ozel_anahtar" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- VERİTABANI AYARLARI (Windows Yerel Postgres) ---
DB_PARAMS = {
    "dbname": "iot_telemetri_db",
    "user": "postgres",
    "password": "903087", # BURAYA KENDİ POSTGRES ŞİFRENİ YAZ (903087 gibi)
    "host": "localhost",        
    "port": "5432"
}

# --- MQTT AYARLARI ---
MQTT_BROKER = "100.127.80.66" # Faruk'un IP adresi
TOPIC = "/cihaz_test/zeyne/telemetry"

# --- MQTT CALLBACK FONKSİYONLARI ---

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("\n✅ BAĞLANTI BAŞARILI: MQTT Broker'a bağlandım.")
        client.subscribe(TOPIC)
        print(f"📡 ABONE OLUNDU: '{TOPIC}' dinleniyor...")
    else:
        print(f"\n❌ BAĞLANTI HATASI: Kod: {rc}")

def on_message(client, userdata, msg):
    print(f"\n📩 YENİ MESAJ GELDİ! Topic: {msg.topic}")
    try:
        payload_str = msg.payload.decode("utf-8", errors="ignore")
        data = json.loads(payload_str)
        
        # Ekran görüntüsündeki tablo sütunlarına göre verileri alıyoruz
        temp = data.get("temperature")
        hum = data.get("humidity")
        pres = data.get("pressure")
        gas = data.get("gas_resistance")
        dust = data.get("dust_raw")

        if temp is not None:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            
            # Tablonla %100 uyumlu INSERT sorgusu (ts, temperature, humidity, pressure, gas_resistance, dust_raw)
            query = """
                INSERT INTO telemetry (ts, temperature, humidity, pressure, gas_resistance, dust_raw, device_internal_id) 
                VALUES (NOW(), %s, %s, %s, %s, %s, %s)
            """
            # device_internal_id için şimdilik varsayılan 1 değerini gönderiyoruz
            cur.execute(query, (float(temp), float(hum), float(pres), float(gas), float(dust), 1))
            
            conn.commit()
            cur.close()
            conn.close()
            print(f"💾 SQL: Veritabanına kaydedildi. (Sıcaklık: {temp})")
    except Exception as e:
        print(f"❌ İŞLEME HATASI: {e}")

# --- MQTT SETUP ---
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, f"Zeynep_PC_{int(time.time())}")
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"❌ MQTT KURULUM HATASI: {e}")

# --- API ENDPOINTLERİ ---

@app.get("/")
def read_index():
    return FileResponse('login.html')

@app.get("/veriler")
def read_veriler():
    return FileResponse('veriler.html')

@app.get("/api/measurement/device/temp/")
async def get_temp_history():
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        # created_at yerine senin tablondaki 'ts' sütununu kullanıyoruz
        cur.execute("SELECT ts, temperature FROM telemetry ORDER BY ts DESC LIMIT 50")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {row[0].strftime("%H:%M:%S"): str(row[1]) for row in reversed(rows)}
    except Exception as e:
        print(f"⚠️ Veri çekme hatası: {e}")
        return {}

if __name__ == "__main__":
    import uvicorn
    # Docker olmadığı için localhost üzerinden çalıştırıyoruz
    uvicorn.run(app, host="127.0.0.1", port=8000)