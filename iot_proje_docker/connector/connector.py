import json
import time

import paho.mqtt.client as mqtt
import psycopg2

DB_PARAMS = {
    "dbname": "iot_telemetri_db",
    "user": "postgres",
    "password": "903087",
    "host": "db",
    "port": "5432",
}

MQTT_BROKER = "mosquitto"
MQTT_TOPIC = "/cihaz_test/zeyne/telemetry"


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connector MQTT bağlı. Topic'e abone olundu:", MQTT_TOPIC, flush=True)
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"❌ Connector MQTT bağlanamadı. rc={rc}", flush=True)



def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)

        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()

        cur.execute("SELECT id FROM devices WHERE device_token = %s", (msg.topic,))
        row = cur.fetchone()
        if not row:
            print(f"⚠️ Tanımsız Topic: {msg.topic}")
            cur.close()
            conn.close()
            return

        device_id = row[0]

        inserted = 0
        for key, val in data.items():
            if key in ("timestamp", "ts", "time"):
                continue
            if isinstance(val, (int, float)):
                cur.execute(
                    """
                    INSERT INTO telemetry (ts, sensor_type, value, device_id)
                    VALUES (NOW(), %s, %s, %s)
                    """,
                    (key, float(val), device_id),
                )
                inserted += 1

        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Connector: {inserted} ölçüm kaydedildi. device_id={device_id}")

    except Exception as e:
        print(f"❌ Connector hata: {e}")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, f"connector_{int(time.time())}")
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, 1883, 60)
client.loop_forever()
