# 🌱 KrishiMitra AI (KisanGPT)

> **Digital Decision Assistant & 1-to-1 Interactive Bilingual Voice Chatbot for Indian Farmers**

KrishiMitra AI is an intelligent agricultural advisory platform designed to empower farmers with location-specific agronomic intelligence and real-time interactive voice guidance.

---

## 🌟 Key Features

### 1. 📍 Farm Geolocation & Parameters with Crop Recommendations
- **Live Location Detection**: Detects device coordinates via GPS sensors or lets users select any Karnataka district.
- **Satellite Soil Classification**: Integrates Google Earth Engine (OpenLandMap 250m) to extract modelled USDA soil texture (Clay loam, Sandy loam, Red sandy loam, etc.).
- **Climate & Temperature Intelligence**: Fetches 7-day rainfall forecasts and temperature windows via Open-Meteo Weather API.
- **AI Crop Recommendation Engine**: Evaluates evidence-based crop suitability (duration, water category, seasonal window, potential risks, and packages of practice).
- **Persistent Farm Profile**: Stores verified farm profiles, acreage, and irrigation parameters in SQLite (`schemes_dev.db`).

### 2. 🎙️ 1-to-1 Interactive Bilingual Voice Chatbot
- **Sarvam AI Human Voice**: Powered by `bulbul:v3` model with natural Indian speakers (`kavya`, `priya`, `aditya`, `rahul`, `roopa`, `ratan`).
- **Bilingual Response Generation**: Every turn generates distinct, clean replies in **Kannada (ಕನ್ನಡ)** and **English**, stored in separate database columns without raw JSON syntax.
- **Single Speaking Language Lock**: Speaks aloud in strictly 1 language (defaulting to Kannada) until the user explicitly requests an audio language change (e.g., *"Please speak in English"* or *"ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡಿ"*).
- **Synchronized Assistant Memory**: Automatically tracks the farmer's district, soil type, temperature, cultivated acreage, water access, and recommended crops.

---

## 🏗️ Project Architecture

```
kisangpt/
├── app.py                     # Unified Modular Flask Backend & API routes
├── voice_chatbot.py           # Bilingual conversational LLM engine & prompt logic
├── sarvam_voice.py            # Sarvam AI Text-to-Speech (TTS) integration
├── chatbot_db.py              # SQLite session, bilingual messages & memory store
├── location_service.py        # Reverse geocoding & environmental intelligence
├── crop_recommender.py        # Regional crop suitability & agronomic rules
├── ai_recommendations.py      # AI decision-support crop evaluation
├── budget_calculator.py       # Cultivation expense breakdown & ROI modeling
├── farming_calendar.py        # 11-phase crop lifecycle calendar engine
├── schemes_dev.db             # SQLite database for sessions & government schemes
├── templates/
│   └── dashboard.html         # Modern dashboard with top-middle menu navigation
├── static/
│   ├── css/dashboard.css      # Polished, responsive design & card styles
│   └── js/
│       ├── dashboard.js       # Geolocation & crop recommendation controller
│       └── voice_assistant.js # Interactive voice recording & playback controller
└── tests/
    ├── test_voice_chatbot.py  # Unit tests for voice chatbot & language lock
    └── test_merged_api.py     # Unit tests for location & recommendation APIs
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.9+
- Git

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/mpremcharan696-coder/kisangpt.git
cd kisangpt

# Install required dependencies
pip install -r requirements_schemes.txt
```

### 3. Environment Configuration
Copy the template `.env.example` to `.env` and insert your API keys:
```bash
cp .env.example .env
```
Edit `.env`:
```env
GROQ_API_KEY=your_groq_api_key_here
SARVAM_API_KEY=your_sarvam_api_key_here
```

### 4. Run the Application
```bash
python app.py
```
Open **`http://127.0.0.1:5000`** in your browser.

---

## 🧪 Testing

Run automated unit and integration tests:
```bash
pytest test_voice_chatbot.py test_merged_api.py -v
```

---

## 📜 License
MIT License.
