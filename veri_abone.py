import paho.mqtt.client as mqtt
import json
import psycopg2
import time
import signal
import sys

# --- Ayarlar ---
# Senin Tailscale IP'n (Broker)
BROKER_ADDRESS = "100.127.80.66" 
BROKER_PORT = 1883
TOPIC = "/cihaz_test/zeyne/telemetry" 
TIMEOUT = 60

# Veritabanı Bilgileri (Windows Yerel Postgres)
DB_PARAMS = {
    "dbname": "iot_telemetri_db",
    "user": "postgres",
    "password": "903087", 
    "host": "localhost",
    "port": "5432"
}

# --- DB bağlantısı ---
def create_connection():
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        print("✅ SQL: PostgreSQL'e bağlantı başarılı.")
        return conn
    except Exception as e:
        print("❌ SQL HATA: Bağlantı kurulamadı:", e)
        return None

def insert_data(conn, sensor_data):
    # Tabloyu yukarıdaki SQL ile oluşturduysan bu sorgu hatasız çalışacaktır
    sql_insert = """ 
        INSERT INTO telemetry (ts, temperature, humidity, pressure, gas_resistance, dust_raw, device_internal_id) 
        VALUES (NOW(), %s, %s, %s, %s, %s, 1)
    """
    cursor = None
    try:
        cursor = conn.cursor()
        # Verilerin sayı olduğundan emin oluyoruz (boş gelirse 0 yazar)
        values = (
            float(sensor_data.get("temperature", 0)),
            float(sensor_data.get("humidity", 0)),
            float(sensor_data.get("pressure", 0)),
            float(sensor_data.get("gas_resistance", 0)),
            float(sensor_data.get("dust_raw", 0))
        )
        cursor.execute(sql_insert, values)
        conn.commit()
        print(f"✅ SQL: Veri kaydedildi! (Sıcaklık: {values[0]})")
    except Exception as e:
        print(f"❌ KAYIT HATASI (Postgres): {e}") # Hata varsa burada göreceğiz
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()

# --- MQTT callback'leri ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("🌐 MQTT: Broker'a bağlantı başarılı.")
        client.subscribe(TOPIC)
        print(f"📡 MQTT: '{TOPIC}' konusu dinleniyor...")
    else:
        print(f"❌ MQTT HATA: Bağlantı kodu: {rc}")

def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode("utf-8", errors="ignore")
        print(f"\n⚡ YENİ MESAJ: {payload_str}")

        sensor_data = json.loads(payload_str)
        
        # Veriyi SQL'e gönder
        db_conn = userdata.get('db_conn')
        if db_conn:
            insert_data(db_conn, sensor_data)
            
    except Exception as e:
        print(f"⚠️ Mesaj işleme hatası: {e}")
        
# --- Program başlatma ---
if __name__ == "__main__":
    db_connection = create_connection()
    if not db_connection:
        sys.exit(1)

    client_id = f"Zeynep_Abone_{int(time.time())}"
    client = mqtt.Client(client_id) 
    client.user_data_set({'db_conn': db_connection})
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        print(f"🔄 MQTT: {BROKER_ADDRESS} adresine bağlanılıyor...")
        client.connect(BROKER_ADDRESS, BROKER_PORT, TIMEOUT)
    except Exception as e:
        print("❌ MQTT bağlantı hatası:", e)
        db_connection.close()
        sys.exit(1)

    client.loop_start()
    print("🚀 MQTT Logger çalışıyor... (Kapatmak için Ctrl+C)")

    def shutdown(signal_received, frame):
        print("\n🛑 Kapatılıyor...")
        client.loop_stop()
        client.disconnect()
        if db_connection:
            db_connection.close()
            print("DB bağlantısı güvenli şekilde kapatıldı.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    
    while True:
        time.sleep(1)