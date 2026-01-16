import psycopg2
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

# --- VERİTABANI AYARLARI ---
DB_PARAMS = {
    "dbname": "iot_telemetri_db",
    "user": "postgres",
    "password": "903087",
    "host": "db",
    "port": "5432",
}

# (API tarafında MQTT yok. MQTT işi connector container'ında.)


def init_db():
    """
    ✅ Doğru yaklaşım:
    - API açılırken telemetry tablosu oluşturmaz.
    - Sadece gerekli index'in varlığını garanti eder.
    - users/devices tabloları yoksa oluşturur (uygulama temeli).
    """
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()

        # 1. Kullanıcılar Tablosu
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
            """
        )

        # 2. Cihazlar Tablosu
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id SERIAL PRIMARY KEY,
                device_name TEXT NOT NULL,
                device_token TEXT UNIQUE NOT NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        # ❌ telemetry tablosu burada oluşturulmuyor (DB şeması migration/manüel yönetilir)

        # ✅ Sadece index garanti altına alınıyor
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_telemetry_device_sensor_ts
            ON telemetry (device_id, sensor_type, ts DESC);
            """
        )

        conn.commit()
        cur.close()
        conn.close()
        print("✅ DB bağlantısı ve index kontrolü tamam.")
    except Exception as e:
        print(f"❌ Veritabanı hatası: {e}")


init_db()


# --- ARAYÜZ SAYFALARI ---
@app.get("/")
async def root():
    return FileResponse("login.html")


@app.get("/kayit")
async def register_page():
    return FileResponse("register.html")


@app.get("/veriler")
async def dashboard():
    return FileResponse("veriler.html")


# --- API ENDPOINTLERİ ---

# ✅ Grafik için genel sensör endpoint’i
# Örnek:
#   /api/device/1/sensor/temperature?limit=50
#   /api/device/1/sensor/humidity?limit=50
@app.get("/api/device/{device_id}/sensor/{sensor_type}")
async def get_sensor_history(device_id: int, sensor_type: str, limit: int = 50):
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()

        cur.execute(
            """
            SELECT ts, value
            FROM telemetry
            WHERE device_id = %s AND sensor_type = %s
            ORDER BY ts DESC
            LIMIT %s
            """,
            (device_id, sensor_type, limit),
        )

        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Grafik için kronolojik sıra (eski -> yeni)
        return [{"time": r[0].strftime("%H:%M:%S"), "value": r[1]} for r in reversed(rows)]

    except Exception as e:
        return {"error": str(e)}


# Sıcaklık geçmişi - eski endpoint (istersen dursun)
@app.get("/api/measurement/device/{device_id}/temp/")
async def get_device_temp_history(device_id: int):
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ts, value
            FROM telemetry
            WHERE device_id = %s AND sensor_type = 'temperature'
            ORDER BY ts DESC
            LIMIT 50
            """,
            (device_id,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return {r[0].strftime("%Y-%m-%d %H:%M:%S"): str(r[1]) for r in rows}
    except Exception as e:
        return {"error": str(e)}


# KULLANICI KAYDI
@app.post("/api/register")
async def register_user(data: dict):
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (data["username"], data["password"]),
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Kayıt başarılı!"}
    except Exception:
        raise HTTPException(status_code=400, detail="Kullanıcı adı alınmış olabilir.")


# CİHAZ YÖNETİMİ
@app.post("/api/devices")
async def create_device(data: dict):
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO devices (device_name, device_token, user_id) VALUES (%s, %s, %s) RETURNING id",
            (data["name"], data["token"], data["user_id"]),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Cihaz tanımlandı", "device_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/login")
async def login_user(data: dict):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (data["username"], data["password"]),
    )
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user:
        return {"message": "Giriş başarılı", "status": "success"}
    else:
        raise HTTPException(status_code=401, detail="Hatalı kullanıcı adı veya şifre")


# Dashboard için son veriler (temp & hum)
@app.get("/api/data")
async def get_all_data(device_id: int = 1, limit: int = 20):
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()

        cur.execute(
            """
            SELECT DISTINCT ts
            FROM telemetry
            WHERE device_id = %s
            ORDER BY ts DESC
            LIMIT %s
            """,
            (device_id, limit),
        )
        ts_rows = [r[0] for r in cur.fetchall()]
        if not ts_rows:
            cur.close()
            conn.close()
            return []

        cur.execute(
            """
            SELECT ts, sensor_type, value
            FROM telemetry
            WHERE device_id = %s
              AND ts = ANY(%s)
              AND sensor_type IN ('temperature', 'humidity')
            """,
            (device_id, ts_rows),
        )
        rows = cur.fetchall()

        cur.close()
        conn.close()

        mapping = {ts: {"zaman": ts.strftime("%H:%M:%S"), "temp": None, "hum": None} for ts in ts_rows}
        for ts, sensor, value in rows:
            if sensor == "temperature":
                mapping[ts]["temp"] = value
            elif sensor == "humidity":
                mapping[ts]["hum"] = value

        return [mapping[ts] for ts in sorted(ts_rows)]

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
