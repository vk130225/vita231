# VITA-INSURATECH - Complete Insurance Platform

## 🚀 **Access Your Website**

**Main Website:** [http://localhost:3000](http://localhost:3000)

## 📋 **System Overview**

Your complete VITA-INSURATECH platform includes:

### **Frontend (User Interface)**
- **URL:** http://localhost:3000
- **Technology:** Next.js with TypeScript & Tailwind CSS
- **Features:** Login, Dashboard, Claims, Pricing, Portfolio

### **Backend (API Services)**
- **URL:** http://localhost:8001
- **Technology:** FastAPI with Python
- **Features:** ML Models, Fraud Detection, Real-time APIs

## 🎯 **Quick Start Guide**

### **1. Access the Website**
Visit: **http://localhost:3000**

### **2. Explore Features**
- **🏠 Landing Page:** Company overview and features
- **🔐 Login:** Authentication (currently demo mode)
- **📊 Dashboard:** Worker overview and claims history
- **💰 Dynamic Pricing:** Interactive premium calculator
- **📈 Portfolio:** Real-time stock market tracking
- **📝 Claim Submission:** AI-powered claim processing

### **3. Test Backend APIs**
```bash
# Health check
curl http://localhost:8001/health

# Test claim processing
curl -X POST http://localhost:8001/claim \
  -H "Content-Type: application/json" \
  -d '{"lat": 12.9716, "lon": 77.5946, "movement": 80, "activity": 75, "location_valid": 1}'
```

## 🔧 **Technical Details**

### **Real Integrations Active:**
- 🌤️ **Weather Data:** Open-Meteo + WeatherAPI
- 🌫️ **Air Quality:** WAQI API
- 🐦 **Social Signals:** Twitter API
- 📊 **Stock Market:** Finnhub API (Real-time data)
- 💳 **Payments:** Razorpay UPI
- 🔐 **Authentication:** Firebase ready

### **AI/ML Features:**
- 6-layer fraud detection pipeline
- Auto-retraining on every claim
- ARCE adaptive risk scoring
- Zone intelligence mapping
- Dynamic pricing based on risk factors

## 📱 **User Journey**

1. **Visit Website** → http://localhost:3000
2. **Explore Landing** → See features and benefits
3. **Login** → Access worker dashboard
4. **Check Portfolio** → View stock investments
5. **Calculate Pricing** → See dynamic premiums
6. **Submit Claim** → AI validation with real data
7. **Monitor Status** → Track claims and earnings

## 🎨 **Design Features**

- **Responsive Design:** Works on all devices
- **Smooth Animations:** Professional transitions
- **Real-time Updates:** Live data integration
- **Interactive Elements:** Sliders, forms, charts
- **Modern UI:** Clean, insurance-industry appropriate

---

**🎉 Your VITA-INSURATECH platform is live and ready for testing!**

**Main Access Link:** [http://localhost:3000](http://localhost:3000)