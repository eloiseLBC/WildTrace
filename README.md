# 🌿 WildTrace

**WildTrace** is an open experimental platform for **environmental data collection**, **biological signal integration**, and **context-aware analysis**, designed for use in real-world, off-grid and nomadic conditions.

The project focuses on **robust data acquisition**, **local-first storage**, and **progressive synchronization**, enabling long-term field experiments without permanent connectivity.

WildTrace is currently in **active development** and serves as a technical and scientific playground for environmental sensing and data exploration.

---

## 🎯 Project Goals

- Collect reliable **environmental data** in diverse and constrained environments  
- Integrate **geolocation and temporal context**  
- Prepare future **biological and physiological data fusion**  
- Ensure **resilience** (offline-first, no data loss)  
- Keep the system **modular, hackable, and extensible**

WildTrace is not a finished product — it is a **research-oriented framework**.

---

## 📊 Data Collected

### 🌡️ Environmental Data
- Temperature  
- Humidity  
- Atmospheric pressure  
- Ambient light  
- CO₂ concentration / air quality (depending on sensors)

### 📍 Geospatial Data
- Latitude  
- Longitude  
- Altitude  
- GPS timestamp  

### ⏱️ Contextual Metadata
- System timestamp  
- Collection session ID  
- Operating mode (normal / debug / offline)

---

## 🧬 Planned Biological & Physiological Data (Future Work)

WildTrace is designed to later integrate **biological signals**, collected via personal wearable devices or external sensors.

Planned data types include:
- Heart rate  
- Heart rate variability (HRV)  
- Sleep phases & duration  
- Physical activity levels  
- Rest / stress indicators  

These data will **not be collected directly by the Raspberry Pi**, but synchronized from external devices (e.g. smartwatches) through APIs or offline exports.

The goal is **data correlation**, not medical diagnosis:  
**environment × physiology × context**.
