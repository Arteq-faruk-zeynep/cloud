# ☁️ IoT Telemetri ve Veri Kayıt Sistemi (Arteq-Faruk-Zeynep)

Bu proje, uzak bir ESP32 cihazından (Faruk) gelen sensör verilerini MQTT protokolü üzerinden dinleyen, işleyen ve yerel bir PostgreSQL veritabanına kaydeden bir IoT bulut altyapısıdır.

## 🚀 Proje Mimarisi

Sistem üç ana bileşenden oluşmaktadır:
1. **Veri Kaynağı (ESP32):** Sıcaklık, nem, basınç, gaz direnci ve toz verilerini JSON formatında MQTT Broker'a yayınlar.
2. **Aracı (MQTT Broker):** Verilerin güvenli bir şekilde taşınmasını sağlar (Tailscale ağı üzerinden).
3. **Veri İşleyici (Python - `veri_abone.py`):** MQTT konusuna abone olur, gelen verileri parse eder ve PostgreSQL'e kaydeder.

## 🛠️ Teknik Detaylar

### 1. Faruk'tan Gelen Veri Formatı
Cihazdan gelen veriler aşağıdaki JSON yapısındadır:
```json
{
  "timestamp": 123456,
  "temperature": 25.5,
  "humidity": 45.0,
  "pressure": 1013.2,
  "gas_resistance": 150.5,
  "dust_raw": 350
}

# ☁️ IoT Telemetri ve Veri Kayıt Sistemi 

Bu proje; uzak bir ESP32 cihazından (Faruk) gelen sensör verilerini MQTT üzerinden dinleyen, işleyen ve yerel bir PostgreSQL veritabanına kaydeden tam kapsamlı bir IoT sistemidir.

## 🛠️ 1. Adım: Veritabanı Kurulumu (PostgreSQL)

Bu projede verilerin kalıcı olarak saklanması için **PostgreSQL** kullanılmıştır. Hiç bilmeyen biri için kurulum adımları:

1. **Yazılım:** [PostgreSQL](https://www.postgresql.org/download/) indirilir ve kurulur.
2. **Arayüz:** Kurulumla birlikte gelen **pgAdmin 4** programı açılır.
3. **Veritabanı Oluşturma:** pgAdmin üzerinde "Databases" kısmına sağ tıklanır -> *Create* -> *Database* seçilir. Adı `iot_telemetri_db` yapılır.
4. **Tablo Oluşturma:** `iot_telemetri_db` üzerine sağ tıklanıp "Query Tool" açılır ve aşağıdaki SQL komutu yapıştırılıp çalıştırılır (F5):

```sql
-- Telemetri verilerinin tutulacağı tabloyu oluşturur
CREATE TABLE telemetry (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    pressure DOUBLE PRECISION,
    gas_resistance DOUBLE PRECISION,
    dust_raw DOUBLE PRECISION,
    device_internal_id INTEGER DEFAULT 1
);
