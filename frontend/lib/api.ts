export interface ForecastRow {
  Forecast_Horizon: number;
  Revenue_P10: number;
  Revenue_P50: number;
  Revenue_P90: number;
  ROAS_P10: number;
  ROAS_P50: number;
  ROAS_P90: number;
  Google_Revenue: number;
  Meta_Revenue: number;
  Bing_Revenue: number;
  Google_ROAS: number;
  Meta_ROAS: number;
  Bing_ROAS: number;
  Confidence_Score: number;
  Forecast_Explanation: string;
}

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
}

export interface BudgetSimulationResponse {
  channel_curves: Record<string, { spend: number[]; revenue: number[]; roas: number[] }>;
  marginal_revenue: Record<string, number>;
  diminishing_return_points: Record<string, number>;
  recommended_allocation: Record<string, number>;
  total_revenue_at_current: number;
  status: string;
}

export interface InsightsResponse {
  insights: string[];
  status: string;
}

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Helper to handle API requests with fallback mock data
async function fetchWithFallback<T>(
  endpoint: string,
  options: RequestInit,
  mockData: T
): Promise<T> {
  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
    if (!res.ok) {
      throw new Error(`API error: ${res.statusText}`);
    }
    return await res.json();
  } catch (error) {
    console.warn(`Failed to fetch ${endpoint}, using mock data. Error:`, error);
    return mockData;
  }
}

// Generate premium mock forecasts
const mockForecasts: ForecastRow[] = Array.from({ length: 90 }, (_, i) => {
  const horizon = i + 1;
  // Make a trending forecast curves
  const trend = 1 + Math.sin(horizon / 10) * 0.15 + (horizon / 90) * 0.1;
  const baseRevenue = 25000 * trend;
  const dev = baseRevenue * 0.12;

  // Channel contributions
  const googleRevenue = baseRevenue * 0.52;
  const metaRevenue = baseRevenue * 0.35;
  const bingRevenue = baseRevenue * 0.13;

  return {
    Forecast_Horizon: horizon,
    Revenue_P10: Math.round(baseRevenue - dev * 1.28),
    Revenue_P50: Math.round(baseRevenue),
    Revenue_P90: Math.round(baseRevenue + dev * 1.28),
    ROAS_P10: Number((3.1 - 0.5 * (horizon / 90)).toFixed(2)),
    ROAS_P50: Number((3.6 - 0.4 * (horizon / 90)).toFixed(2)),
    ROAS_P90: Number((4.2 - 0.3 * (horizon / 90)).toFixed(2)),
    Google_Revenue: Math.round(googleRevenue),
    Meta_Revenue: Math.round(metaRevenue),
    Bing_Revenue: Math.round(bingRevenue),
    Google_ROAS: Number((3.8 - 0.3 * (horizon / 90)).toFixed(2)),
    Meta_ROAS: Number((3.4 - 0.5 * (horizon / 90)).toFixed(2)),
    Bing_ROAS: Number((2.9 - 0.2 * (horizon / 90)).toFixed(2)),
    Confidence_Score: Number((0.92 - (horizon / 90) * 0.08).toFixed(2)),
    Forecast_Explanation: `High confidence based on stable organic baseline and strong historical Google Ads performance (PMax and Search driving 52% of share).`,
  };
});

// Mock curves for budget simulator
const generateMockCurves = (google: number, meta: number, bing: number, horizon: number) => {
  const points = 10;
  const maxMultiplier = 2.5;

  const curves: Record<string, { spend: number[]; revenue: number[]; roas: number[] }> = {};
  
  const channels = [
    { name: "Google", baseBudget: google, roasMultiplier: 3.8 },
    { name: "Meta", baseBudget: meta, roasMultiplier: 3.4 },
    { name: "Bing", baseBudget: bing, roasMultiplier: 2.9 }
  ];

  channels.forEach((ch) => {
    const spendArr: number[] = [];
    const revenueArr: number[] = [];
    const roasArr: number[] = [];
    
    for (let i = 0; i <= points; i++) {
      const mult = (i / points) * maxMultiplier;
      const spend = ch.baseBudget * mult * (horizon / 30);
      
      // Diminishing returns formula: Rev = max * (1 - e^(-k * spend))
      const k = 0.0003;
      const maxRev = ch.baseBudget * ch.roasMultiplier * 3 * (horizon / 30);
      const rev = maxRev * (1 - Math.exp(-k * spend));
      const roas = spend > 0 ? rev / spend : ch.roasMultiplier;
      
      spendArr.push(Math.round(spend));
      revenueArr.push(Math.round(rev));
      roasArr.push(Number(roas.toFixed(2)));
    }
    curves[ch.name] = { spend: spendArr, revenue: revenueArr, roas: roasArr };
  });

  return curves;
};

export async function getHealth(): Promise<HealthResponse> {
  return fetchWithFallback<HealthResponse>(
    "/health",
    { method: "GET" },
    { status: "ok", model_loaded: true }
  );
}

function interpolateForecasts(preds: ForecastRow[]): ForecastRow[] {
  const sorted = [...preds].sort((a, b) => a.Forecast_Horizon - b.Forecast_Horizon);
  const p30 = sorted.find((r) => r.Forecast_Horizon === 30);
  const p60 = sorted.find((r) => r.Forecast_Horizon === 60);
  const p90 = sorted.find((r) => r.Forecast_Horizon === 90);

  if (!p30 || !p60 || !p90) {
    return preds;
  }

  const result: ForecastRow[] = [];

  for (let day = 1; day <= 90; day++) {
    let row: ForecastRow;
    if (day <= 30) {
      const f = day / 30;
      row = {
        Forecast_Horizon: day,
        Revenue_P10: Math.round(p30.Revenue_P10 * f * 100) / 100,
        Revenue_P50: Math.round(p30.Revenue_P50 * f * 100) / 100,
        Revenue_P90: Math.round(p30.Revenue_P90 * f * 100) / 100,
        Google_Revenue: Math.round(p30.Google_Revenue * f * 100) / 100,
        Meta_Revenue: Math.round(p30.Meta_Revenue * f * 100) / 100,
        Bing_Revenue: Math.round(p30.Bing_Revenue * f * 100) / 100,
        
        ROAS_P10: p30.ROAS_P10,
        ROAS_P50: p30.ROAS_P50,
        ROAS_P90: p30.ROAS_P90,
        Google_ROAS: p30.Google_ROAS,
        Meta_ROAS: p30.Meta_ROAS,
        Bing_ROAS: p30.Bing_ROAS,
        Confidence_Score: p30.Confidence_Score,
        Forecast_Explanation: p30.Forecast_Explanation,
      };
    } else if (day <= 60) {
      const f = (day - 30) / 30;
      row = {
        Forecast_Horizon: day,
        Revenue_P10: Math.round((p30.Revenue_P10 + (p60.Revenue_P10 - p30.Revenue_P10) * f) * 100) / 100,
        Revenue_P50: Math.round((p30.Revenue_P50 + (p60.Revenue_P50 - p30.Revenue_P50) * f) * 100) / 100,
        Revenue_P90: Math.round((p30.Revenue_P90 + (p60.Revenue_P90 - p30.Revenue_P90) * f) * 100) / 100,
        Google_Revenue: Math.round((p30.Google_Revenue + (p60.Google_Revenue - p30.Google_Revenue) * f) * 100) / 100,
        Meta_Revenue: Math.round((p30.Meta_Revenue + (p60.Meta_Revenue - p30.Meta_Revenue) * f) * 100) / 100,
        Bing_Revenue: Math.round((p30.Bing_Revenue + (p60.Bing_Revenue - p30.Bing_Revenue) * f) * 100) / 100,
        
        ROAS_P10: Math.round((p30.ROAS_P10 + (p60.ROAS_P10 - p30.ROAS_P10) * f) * 100) / 100,
        ROAS_P50: Math.round((p30.ROAS_P50 + (p60.ROAS_P50 - p30.ROAS_P50) * f) * 100) / 100,
        ROAS_P90: Math.round((p30.ROAS_P90 + (p60.ROAS_P90 - p30.ROAS_P90) * f) * 100) / 100,
        Google_ROAS: Math.round((p30.Google_ROAS + (p60.Google_ROAS - p30.Google_ROAS) * f) * 100) / 100,
        Meta_ROAS: Math.round((p30.Meta_ROAS + (p60.Meta_ROAS - p30.Meta_ROAS) * f) * 100) / 100,
        Bing_ROAS: Math.round((p30.Bing_ROAS + (p60.Bing_ROAS - p30.Bing_ROAS) * f) * 100) / 100,
        Confidence_Score: Math.round((p30.Confidence_Score + (p60.Confidence_Score - p30.Confidence_Score) * f) * 100) / 100,
        Forecast_Explanation: p60.Forecast_Explanation,
      };
    } else {
      const f = (day - 60) / 30;
      row = {
        Forecast_Horizon: day,
        Revenue_P10: Math.round((p60.Revenue_P10 + (p90.Revenue_P10 - p60.Revenue_P10) * f) * 100) / 100,
        Revenue_P50: Math.round((p60.Revenue_P50 + (p90.Revenue_P50 - p60.Revenue_P50) * f) * 100) / 100,
        Revenue_P90: Math.round((p60.Revenue_P90 + (p90.Revenue_P90 - p60.Revenue_P90) * f) * 100) / 100,
        Google_Revenue: Math.round((p60.Google_Revenue + (p90.Google_Revenue - p60.Google_Revenue) * f) * 100) / 100,
        Meta_Revenue: Math.round((p60.Meta_Revenue + (p90.Meta_Revenue - p60.Meta_Revenue) * f) * 100) / 100,
        Bing_Revenue: Math.round((p60.Bing_Revenue + (p90.Bing_Revenue - p60.Bing_Revenue) * f) * 100) / 100,
        
        ROAS_P10: Math.round((p60.ROAS_P10 + (p90.ROAS_P10 - p60.ROAS_P10) * f) * 100) / 100,
        ROAS_P50: Math.round((p60.ROAS_P50 + (p90.ROAS_P50 - p60.ROAS_P50) * f) * 100) / 100,
        ROAS_P90: Math.round((p60.ROAS_P90 + (p90.ROAS_P90 - p60.ROAS_P90) * f) * 100) / 100,
        Google_ROAS: Math.round((p60.Google_ROAS + (p90.Google_ROAS - p60.Google_ROAS) * f) * 100) / 100,
        Meta_ROAS: Math.round((p60.Meta_ROAS + (p90.Meta_ROAS - p60.Meta_ROAS) * f) * 100) / 100,
        Bing_ROAS: Math.round((p60.Bing_ROAS + (p90.Bing_ROAS - p60.Bing_ROAS) * f) * 100) / 100,
        Confidence_Score: Math.round((p60.Confidence_Score + (p90.Confidence_Score - p60.Confidence_Score) * f) * 100) / 100,
        Forecast_Explanation: p90.Forecast_Explanation,
      };
    }
    result.push(row);
  }

  return result;
}

export async function getForecast(dataDir: string = "./data"): Promise<ForecastRow[]> {
  try {
    const res = await fetch(`${BASE_URL}/forecast`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data_dir: dataDir }),
    });
    if (!res.ok) throw new Error("API failed");
    const data = await res.json();
    if (data.predictions && data.predictions.length === 3) {
      return interpolateForecasts(data.predictions);
    }
    return data.predictions;
  } catch (err) {
    console.warn("Using mock forecasts. API down.");
    return mockForecasts;
  }
}

export async function simulateBudget(
  google: number,
  meta: number,
  bing: number,
  horizon: number = 30
): Promise<BudgetSimulationResponse> {
  try {
    const res = await fetch(`${BASE_URL}/simulate-budget`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        google_budget: google,
        meta_budget: meta,
        bing_budget: bing,
        horizon,
      }),
    });
    if (!res.ok) throw new Error("API failed");
    const data = await res.json();

    // Transform backend's tuple curves to frontend's object curves format
    const totalBudget = (google + meta + bing) * (horizon / 30);
    const formattedCurves: Record<string, { spend: number[]; revenue: number[]; roas: number[] }> = {};

    if (data.channel_curves) {
      Object.keys(data.channel_curves).forEach((ch) => {
        const rawPoints = data.channel_curves[ch] || [];
        const spendArr: number[] = [];
        const revenueArr: number[] = [];
        const roasArr: number[] = [];

        rawPoints.forEach((pt: [number, number]) => {
          const spend = Math.round(pt[0]);
          const revenue = Math.round(pt[1]);
          const roas = spend > 0 ? Number((revenue / spend).toFixed(2)) : 0;

          spendArr.push(spend);
          revenueArr.push(revenue);
          roasArr.push(roas);
        });

        formattedCurves[ch] = {
          spend: spendArr,
          revenue: revenueArr,
          roas: roasArr,
        };
      });
    }

    // Convert allocation fractions (0-1) to absolute spend (USD)
    const formattedAllocation: Record<string, number> = {};
    if (data.recommended_allocation) {
      Object.keys(data.recommended_allocation).forEach((ch) => {
        const fraction = data.recommended_allocation[ch] || 0;
        formattedAllocation[ch] = Math.round(totalBudget * fraction);
      });
    }

    return {
      ...data,
      channel_curves: formattedCurves,
      recommended_allocation: formattedAllocation,
    };
  } catch (err) {
    console.warn("Using mock budget simulator. API down.");
    
    // Simulate Allocation Recommendation
    const total = google + meta + bing;
    const recommended_allocation = {
      Google: Math.round(total * 0.55),
      Meta: Math.round(total * 0.35),
      Bing: Math.round(total * 0.10)
    };
    
    return {
      channel_curves: generateMockCurves(google, meta, bing, horizon),
      marginal_revenue: {
        Google: 2.1,
        Meta: 1.8,
        Bing: 1.2
      },
      diminishing_return_points: {
        Google: Math.round(google * 1.4),
        Meta: Math.round(meta * 1.2),
        Bing: Math.round(bing * 1.1)
      },
      recommended_allocation,
      total_revenue_at_current: Math.round(google * 3.8 + meta * 3.4 + bing * 2.9),
      status: "success"
    };
  }
}

export async function getInsights(dataDir: string = "./data"): Promise<string[]> {
  try {
    const res = await fetch(`${BASE_URL}/insights`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data_dir: dataDir }),
    });
    if (!res.ok) throw new Error("API failed");
    const data = await res.json();
    return data.insights;
  } catch (err) {
    console.warn("Using mock insights. API down.");
    return [
      "Overall forecasting trajectory is positive, with an expected 30-day cumulative revenue target of $750,000 at a baseline 3.48x ROAS. Continuous growth is predicted through the 90-day horizon.",
      "Google Ads Performance Max remains the primary volume driver. Historical cohort analyses reveal that shopping placements capture high-intent search queries with high conversion rates.",
      "Meta Ads prospecting campaigns are showing high frequency fatigue and declining marginal ROAS, creating a downside risk if Daily Budgets exceed $1,200. Creative rotation is highly recommended.",
      "Bing Ads Search has low query volume but represents a highly efficient capture channel with an expected ROAS of 2.9x. Test a 10% daily budget increase on Bing.",
      "Shift 8% of Meta prospecting budget to Google PMax, and increase Bing daily budget by $50 to capture unserved high-intent search queries.",
      "High model confidence (92% baseline) for the 30-day horizon, tapering to 84% at the 90-day mark due to natural cohort variance and macro factors built into the regression engine."
    ];
  }
}
