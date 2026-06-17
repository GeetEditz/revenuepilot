# RevenuePilot AI
> **AI-Assisted Probabilistic Revenue Forecasting & Budget Optimization for Ecommerce Marketing**

RevenuePilot AI is an enterprise-grade ecommerce revenue forecasting and budget simulation platform. It features a machine learning forecasting engine (LightGBM Quantile Regression) combined with a FastAPI backend and a Next.js (React 19) client dashboard. The platform generates probabilistic intervals (P10/P50/P90) for future revenue and ROAS across Google Ads, Meta Ads, and Microsoft/Bing Ads, optimizing ad spend split recommendations using Llama-3.1 via NVIDIA NIM microservices.

---

## 🚀 Key Features

* **Probabilistic Forecasting Engine**: Powered by LightGBM Quantile Regression models to output P10 (pessimistic), P50 (expected median), and P90 (optimistic) confidence ranges over 30, 60, and 90-day horizons.
* **Interactive Budget Simulator**: A visual simulator demonstrating multi-channel spending curves, diminishing returns limits, and recommended budget splits.
* **High-Fidelity UI Controls**: Uses custom `ElasticSlider` components with rubber-band dragging, magnetic snapping, and discrete hash markings alongside text inputs cleaned to hide default number spinner arrows.
* **Full-Screen Blurred Loader Overlay**: A sleek loading screen built with a CSS grid ripple animation and a high z-index backdrop blur that holds focus until the simulation query returns from the backend.
* **Enterprise Notification System**: A custom-built, state-driven Toast system for real-time success/info notifications (e.g. simulation completion, budget resets).
* **Live Telemetry & Diagnostics**: Navbar indicator tracking backend gateway connection status and model loading readiness (Model Ready / Fallback Ready).
* **NVIDIA NIM Strategic AI Insights**: Connects to the Llama-3.1 LLM via NVIDIA NIM API to produce exactly 6 distinct strategic analysis sections:
  1. *Executive Summary* (projected revenues and blended ROAS targets)
  2. *Growth Drivers* (search and shopping performance splits)
  3. *Revenue Risks* (creative fatigue, marginal return thresholds)
  4. *Campaign Opportunities* (long-tail queries, Bing and PMax margins)
  5. *Budget Recommendations* (optimal splits between Google, Meta, and Bing)
  6. *Confidence Explanation* (interval regressions and quantile variance bounds)
* **Offline Resilience**: Automatically triggers a detailed, rule-based fallback report generator to construct all 6 categories directly from LightGBM predictions if the LLM microservice is offline or credentials are missing.
* **Smart Caching & State Management**: Integrated with TanStack Query (React Query) to prevent duplicate API fetches on route transitions, navigation, or component re-renders.

---

## 🛠️ System Architecture

```
                       ┌───────────────────────────────────────┐
                       │           REVENUEPILOT AI             │
                       │           (Next.js Client)            │
                       └──────────────────┬────────────────────┘
                                          │
                                   HTTP / JSON REST
                                          │
                       ┌──────────────────▼────────────────────┐
                       │            FASTAPI GATEWAY            │
                       │          (Backend API Port)           │
                       └────┬─────────────────────────────┬────┘
                            │                             │
                            │ (Predict & Simulate)        │ (Strategic Prompting)
                            │                             │
               ┌────────────▼────────────┐   ┌────────────▼────────────┐
               │    FORECASTING ENGINE   │   │       NVIDIA NIM        │
               │   (LightGBM model.pkl)  │   │   (Llama-3.1-70B API)   │
               └─────────────────────────┘   └─────────────────────────┘
```

### File Hierarchy & Component Breakdown

```
├── run.sh                          # Execution pipeline entrypoint
├── requirements.txt                # Python backend dependencies
├── README.md                       # Platform documentation
├── data/                           # Ingestion folder for campaign CSVs
│   ├── bing_campaign_stats.csv     
│   ├── google_ads_campaign_stats.csv
│   └── meta_ads_campaign_stats.csv 
├── output/                         
│   └── predictions.csv             # Ingested pipeline output file
├── pickle/                         
│   └── model.pkl                   # Quantile regression weights binary
├── logs/                           # System diagnostic log directories
│   ├── app.log                     # Application runtime logs
│   ├── errors.log                  # Critical errors trace logs
│   ├── api.log                     # Middleware REST routes analytics
│   └── forecast.log                # Forecasting engine metrics
├── backend/                        
│   ├── main.py                     # FastAPI application router & server config
│   └── ...                         
├── frontend/                       
│   ├── package.json                # Next.js configurations & dependencies
│   ├── tsconfig.json               # Path alias and compiler settings
│   ├── components.json             # shadcn components config
│   ├── providers/                  
│   │   └── query-provider.tsx      # React Query Provider setup
│   ├── hooks/                      
│   │   ├── use-toast.tsx           # Global Toast state provider and layout
│   │   └── use-controllable-state.tsx
│   ├── components/                 
│   │   ├── dashboard-shell.tsx     # Shell navigation layout and telemetry indicators
│   │   ├── loader.tsx              # Grid ripple backdrop blur loader
│   │   ├── elastic-slider.tsx      # Custom dynamic slider component
│   │   └── ui/                     # Prerendered UI building blocks
│   └── app/                        
│       ├── page.tsx                # Homepage dashboard and probabilistic forecast charts
│       ├── simulator/              # Simulator page, sliders, inputs, response charts
│       ├── insights/               # AI generated Strategic Advisory Report
│       ├── health/                 # Health diagnostics and platform telemetry gauges
│       └── globals.css             # Tailwind v4 directives and CSS theme variables
├── src/                            
│   ├── preprocessing.py            # Normalizes 100+ raw column names to unified grain
│   ├── validation.py               # Handles NaN, negative costs, and IQR outliers
│   ├── generate_features.py        # Generates 44+ rolling, lag, trend, and cyclical features
│   ├── forecasting.py              # LightGBM model training wrapper
│   ├── train.py                    # Quantile regression model pipeline training script
│   ├── predict.py                  # Predicts target revenue intervals from feature frames
│   ├── budget_simulator.py         # Multi-channel spending returns response curves
│   └── ai_insights.py              # LLM NVIDIA NIM microservices prompts and parser
```

---

## 📈 ML Forecasting Methodology

### LightGBM Quantile Regression
The core model contains three quantile regression configurations trained on the same engineering vectors to estimate prediction intervals:
* **P10** (Quantile $\alpha = 0.10$): Estimating pessimistic lower boundaries.
* **P50** (Quantile $\alpha = 0.50$): Median expected performance target.
* **P90** (Quantile $\alpha = 0.90$): Optimistic upper boundary.

### Target Formulation
For each historical timestamp $t$ and specific `(Channel, CampaignType)`, the model fits:
$$\text{Target}_h = \sum_{k=t+1}^{t+h} \text{Revenue}_k \quad \text{for } h \in \{30, 60, 90\}$$
The `Forecast_Horizon` is parameterized as an integer feature ($30$, $60$, or $90$), allowing a single model to learn mapping dimensions across all three target windows.

### Feature Space (44+ Metrics)
The feature engineering pipeline transforms raw metrics into predictive signals:
1. **Ratio Dynamics**: CTR, CPC, CPA, ROAS, conversion rates.
2. **Lags**: Revenue lag 7/14/30, spend lag 7/14, ROAS lag 7.
3. **Rolling Stats**: 7/14/30-day moving averages and standard deviations.
4. **Trend Slopes**: 14-day performance slope lines.
5. **Cyclical Seasonality**: Cyclical encoding of temporal bounds using sine/cosine transforms:
   $$\sin\left(\frac{2\pi \cdot \text{week}}{52}\right), \quad \cos\left(\frac{2\pi \cdot \text{week}}{52}\right)$$
6. **Market Concentration**: Channel revenue/spend share.
7. **Cyclical Indicators**: Month, week of year, day of week, quarters, month boundaries.

---

## 🖥️ Getting Started

### Prerequisites
* Python 3.10+ (compatible with Python 3.13)
* Node.js v18+ & npm

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd hackaton
   ```

2. **Set up Python Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install Frontend Dependencies**:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

### Running the ML Prediction Pipeline
Run the baseline prediction pipeline on data files:
```bash
# In the project root:
bash run.sh ./data ./pickle/model.pkl ./output/predictions.csv
```
This runs:
1. **Ingestion & Validation**: Cleans CSV campaigns in `./data`.
2. **Feature Engineering**: Generates the 44+ features list.
3. **Inference**: Generates probabilistic results in `./output/predictions.csv`.

---

## ⚡ Running the Platform Locally

### 1. Start the Backend API Server
Configure the NVIDIA NIM API credentials (optional, fallback rule-based generation is used if missing) and start FastAPI:
```bash
# Set your NVIDIA NIM API Key:
# Windows (PowerShell):
$env:NVIDIA_API_KEY="your-nvidia-api-key-here"
# Linux/macOS:
export NVIDIA_API_KEY="your-nvidia-api-key-here"

# Start the server:
python -m backend.main
```
The backend server runs on `http://localhost:8000`.

### 2. Start the Frontend Dashboard
Open a new terminal window:
```bash
cd frontend
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 🧪 Testing & Verification

Ensure platform compliance with backend regression checks:
```bash
# Run backend validation test suites
python scripts/verify_submission.py
```
This evaluates data consistency, CPU portability, missing file fallbacks, and prediction formatting constraints.

---

## 📝 Configuration & Output Schema

The predictions output matches the mandatory structure:
```csv
Forecast_Horizon,Revenue_P10,Revenue_P50,Revenue_P90,ROAS_P10,ROAS_P50,ROAS_P90,Google_Revenue,Google_ROAS,Meta_Revenue,Meta_ROAS,Bing_Revenue,Bing_ROAS,Confidence_Score,Forecast_Explanation
30,75000,90000,110000,2.1,2.5,3.1,45000,2.6,35000,2.4,10000,2.2,0.85,"AI Strategic summary report..."
60,145000,175000,210000,2.0,2.4,3.0,88000,2.5,67000,2.3,20000,2.1,0.82,"AI Strategic summary report..."
90,210000,250000,300000,1.9,2.3,2.9,125000,2.4,95000,2.2,30000,2.0,0.78,"AI Strategic summary report..."
```
