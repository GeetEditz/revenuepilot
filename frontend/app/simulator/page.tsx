"use client";

import React, { useState, useMemo, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { ElasticSlider } from "@/components/elastic-slider";
import Loader from "@/components/loader";
import { useToast } from "@/hooks/use-toast";
import {
  Sliders,
  DollarSign,
  TrendingUp,
  Percent,
  Play,
  RotateCcw,
  Sparkles,
  Info,
  TrendingDown,
  ArrowRight,
  TrendingUp as LiftIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { BudgetSimulationResponse } from "@/lib/api";
import { useForecast, useBudgetSimulation } from "@/lib/hooks/useQueries";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  Legend,
  ReferenceDot,
  BarChart,
  Bar,
  Cell
} from "recharts";
import { Skeleton } from "@/components/ui/skeleton";
 
export default function BudgetSimulator() {
  const { toast } = useToast();

  const [googleBudget, setGoogleBudget] = useState<number>(1200);
  const [metaBudget, setMetaBudget] = useState<number>(800);
  const [bingBudget, setBingBudget] = useState<number>(300);
  const [horizon, setHorizon] = useState<number>(30);

  const [googleSim, setGoogleSim] = useState<number>(1200);
  const [metaSim, setMetaSim] = useState<number>(800);
  const [bingSim, setBingSim] = useState<number>(300);
  const [horizonSim, setHorizonSim] = useState<number>(30);

  const [isSimulating, setIsSimulating] = useState(false);
 
  // TanStack Query hooks with simulator parameters
  const { data: forecastData } = useForecast();
  const { simulation, isLoading: loading } = useBudgetSimulation(
    googleSim, metaSim, bingSim, horizonSim
  );

  const handleStartSimulation = () => {
    setIsSimulating(true);
    setGoogleSim(googleBudget);
    setMetaSim(metaBudget);
    setBingSim(bingBudget);
    setHorizonSim(horizon);
  };

  useEffect(() => {
    if (isSimulating && !loading) {
      const timer = setTimeout(() => {
        setIsSimulating(false);
        toast({
          title: "Simulation Completed",
          description: "Multi-channel budgets recalculated successfully.",
          type: "success",
        });
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [loading, isSimulating, toast]);
 
  // Baseline revenue from forecast data using simulated horizon
  const baselineRevenue = useMemo(() => {
    if (!forecastData || forecastData.length === 0) return 0;
    const row = forecastData[Math.min(horizonSim - 1, forecastData.length - 1)];
    return row.Revenue_P50;
  }, [forecastData, horizonSim]);
 
  const resetBudgets = () => {
    setGoogleBudget(1200);
    setMetaBudget(800);
    setBingBudget(300);
    setGoogleSim(1200);
    setMetaSim(800);
    setBingSim(300);
    toast({
      title: "Budgets Reset",
      description: "Channel budgets restored to default baseline configuration.",
      type: "info",
    });
  };
 
  // Process data for charts
  const getCurveData = useCallback((channel: string) => {
    if (!simulation || !simulation.channel_curves || !simulation.channel_curves[channel]) return [];
    const curve = simulation.channel_curves[channel];
    return curve.spend.map((s: number, idx: number) => ({
      spend: s,
      revenue: curve.revenue[idx],
      roas: curve.roas[idx],
    }));
  }, [simulation]);
 
  const googleCurve = useMemo(() => getCurveData("Google"), [getCurveData]);
  const metaCurve = useMemo(() => getCurveData("Meta"), [getCurveData]);
  const bingCurve = useMemo(() => getCurveData("Bing"), [getCurveData]);
 
  // Sum active budget & simulate output using simulated values
  const totalBudget = googleSim + metaSim + bingSim;
  const simulatedRevenue = simulation
    ? Object.keys(simulation.channel_curves).reduce((sum, ch) => {
        // Find nearest spend point in curves
        const curve = simulation.channel_curves[ch];
        if (!curve) return sum;
        const targetSpend = (ch === "Google" ? googleSim : ch === "Meta" ? metaSim : bingSim) * (horizonSim / 30);
        // Find closest spend index
        let closestIdx = 0;
        let minDiff = Infinity;
        curve.spend.forEach((s: number, idx: number) => {
          const diff = Math.abs(s - targetSpend);
          if (diff < minDiff) {
            minDiff = diff;
            closestIdx = idx;
          }
        });
        return sum + curve.revenue[closestIdx];
      }, 0)
    : googleSim * 3.8 + metaSim * 3.4 + bingSim * 2.9;
 
  const simulatedROAS = totalBudget > 0 ? simulatedRevenue / (totalBudget * (horizonSim / 30)) : 0;
  const baselineCost = 2300 * (horizonSim / 30); // Baseline spend estimation
  const revenueLift = simulatedRevenue - baselineRevenue;
  const liftPct = baselineRevenue > 0 ? (revenueLift / baselineRevenue) * 100 : 0;
 
  // Pie chart data for recommended split
  const recommendedData = simulation && simulation.recommended_allocation
    ? Object.entries(simulation.recommended_allocation).map(([name, amount]) => ({
        name,
        value: amount,
      }))
    : [
        { name: "Google Ads", value: totalBudget * 0.55 },
        { name: "Meta Ads", value: totalBudget * 0.35 },
        { name: "Bing Ads", value: totalBudget * 0.10 },
      ];
 
  const currentAllocationData = [
    { name: "Google Ads", value: googleSim },
    { name: "Meta Ads", value: metaSim },
    { name: "Bing Ads", value: bingSim },
  ];
 
  return (
    <>
      {isSimulating && <Loader />}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="space-y-8"
      >
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Budget Simulator</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Simulate channel budget variations and discover optimal multi-channel spend allocations
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-semibold uppercase mr-1">Horizon:</span>
          {[30, 60, 90].map((h) => (
            <Button
              key={h}
              variant={horizon === h ? "default" : "outline"}
              size="sm"
              onClick={() => setHorizon(h as any)}
              className="h-8 px-3 text-xs"
            >
              {h} Days
            </Button>
          ))}
        </div>
      </div>

      {/* Inputs & Outputs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Inputs */}
        <Card className="shadow-sm border-border bg-card lg:col-span-1">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg font-semibold tracking-tight">Simulator Controls</CardTitle>
            <CardDescription className="text-xs">Adjust daily media budgets for each channel</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Google Daily Budget */}
            <div className="flex gap-4 items-center">
              <div className="flex-1">
                <ElasticSlider
                  label="Google Ads"
                  min={0}
                  max={5000}
                  step={50}
                  value={googleBudget}
                  onValueChange={setGoogleBudget}
                  formatValue={(v) => `$${Math.round(v).toLocaleString()}`}
                  className="[--elastic-slider-handle:var(--color-primary)] [--elastic-slider-label:var(--color-primary)] [--elastic-slider-fill:var(--color-primary)]/10 [--elastic-slider-fill-active:var(--color-primary)]/20"
                />
              </div>
              <Input
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                value={googleBudget === 0 ? "" : googleBudget}
                onChange={(e) => {
                  const val = e.target.value.replace(/\D/g, "");
                  setGoogleBudget(val === "" ? 0 : Number(val));
                }}
                className="w-20 h-8 text-xs font-bold text-right"
              />
            </div>

            {/* Meta Daily Budget */}
            <div className="flex gap-4 items-center">
              <div className="flex-1">
                <ElasticSlider
                  label="Meta Ads"
                  min={0}
                  max={5000}
                  step={50}
                  value={metaBudget}
                  onValueChange={setMetaBudget}
                  formatValue={(v) => `$${Math.round(v).toLocaleString()}`}
                  className="[--elastic-slider-handle:oklch(0.769_0.188_70.08)] [--elastic-slider-label:oklch(0.769_0.188_70.08)] [--elastic-slider-fill:oklch(0.769_0.188_70.08)]/10 [--elastic-slider-fill-active:oklch(0.769_0.188_70.08)]/20"
                />
              </div>
              <Input
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                value={metaBudget === 0 ? "" : metaBudget}
                onChange={(e) => {
                  const val = e.target.value.replace(/\D/g, "");
                  setMetaBudget(val === "" ? 0 : Number(val));
                }}
                className="w-20 h-8 text-xs font-bold text-right"
              />
            </div>

            {/* Bing Daily Budget */}
            <div className="flex gap-4 items-center">
              <div className="flex-1">
                <ElasticSlider
                  label="Bing Ads"
                  min={0}
                  max={2500}
                  step={50}
                  value={bingBudget}
                  onValueChange={setBingBudget}
                  formatValue={(v) => `$${Math.round(v).toLocaleString()}`}
                  className="[--elastic-slider-handle:oklch(0.627_0.194_149.22)] [--elastic-slider-label:oklch(0.627_0.194_149.22)] [--elastic-slider-fill:oklch(0.627_0.194_149.22)]/10 [--elastic-slider-fill-active:oklch(0.627_0.194_149.22)]/20"
                />
              </div>
              <Input
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                value={bingBudget === 0 ? "" : bingBudget}
                onChange={(e) => {
                  const val = e.target.value.replace(/\D/g, "");
                  setBingBudget(val === "" ? 0 : Number(val));
                }}
                className="w-20 h-8 text-xs font-bold text-right"
              />
            </div>

            <div className="pt-4 border-t border-border flex gap-2 items-center">
              <Button 
                onClick={handleStartSimulation} 
                className="flex-1 h-9 font-bold bg-primary hover:bg-primary/90 text-primary-foreground flex items-center justify-center gap-2"
              >
                <Sparkles className="h-4 w-4 animate-pulse" />
                Start Simulation
              </Button>
              <Button variant="outline" onClick={resetBudgets} className="h-9 px-3">
                <RotateCcw className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Comparison Dashboard: Current State vs Projected State */}
        <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Baseline Strategy */}
          <Card className="border border-border bg-card/40 relative overflow-hidden transition-all duration-300">
            <CardHeader className="pb-3">
              <div className="flex justify-between items-center">
                <Badge variant="outline" className="text-[10px] tracking-wider uppercase font-semibold text-muted-foreground border-border bg-muted/40">Baseline Setup</Badge>
                <span className="text-[10px] text-muted-foreground font-medium">Daily Spend: $2,300</span>
              </div>
              <CardTitle className="text-xl font-bold tracking-tight text-muted-foreground mt-2">Current Strategy</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5 pt-1">
              <div className="space-y-1">
                <span className="text-xs text-muted-foreground font-medium">Expected Revenue ({horizonSim}d)</span>
                <div className="text-3xl font-bold tracking-tight text-muted-foreground">{formatCurrency(baselineRevenue)}</div>
              </div>
              <div className="space-y-1">
                <span className="text-xs text-muted-foreground font-medium">Blended ROAS Target</span>
                <div className="text-3xl font-bold tracking-tight text-muted-foreground">3.48x</div>
              </div>
              <div className="text-xs text-muted-foreground flex gap-1 items-center border-t border-border pt-3">
                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground" />
                <span>Standard historical performance baseline</span>
              </div>
            </CardContent>
          </Card>
 
          {/* Simulated Strategy */}
          <Card className="border-2 border-primary bg-card relative overflow-hidden shadow-lg transition-all duration-300 hover:shadow-primary/5">
            {/* Ambient subtle glow background */}
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent pointer-events-none" />
            <CardHeader className="pb-3">
              <div className="flex justify-between items-center">
                <Badge className="text-[10px] tracking-wider uppercase font-semibold text-primary-foreground bg-primary border-transparent">Simulated Setup</Badge>
                <span className="text-[10px] text-foreground font-bold">Daily Spend: ${totalBudget.toLocaleString()}</span>
              </div>
              <CardTitle className="text-xl font-bold tracking-tight text-foreground mt-2">Projected Strategy</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5 pt-1 relative z-10">
              <div className="space-y-1">
                <span className="text-xs text-muted-foreground font-medium">Projected Revenue ({horizonSim}d)</span>
                <div className="text-3xl font-extrabold tracking-tight text-foreground">{formatCurrency(simulatedRevenue)}</div>
              </div>
              <div className="space-y-1">
                <span className="text-xs text-muted-foreground font-medium">Simulated Blended ROAS</span>
                <div className="text-3xl font-extrabold tracking-tight text-primary">{simulatedROAS.toFixed(2)}x</div>
              </div>
              
              <div className="border-t border-border pt-3 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <LiftIcon className="h-4 w-4 text-emerald-500 shrink-0" />
                  <span className="text-xs text-muted-foreground font-medium">Net Revenue Lift:</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={cn("text-xs font-bold px-2 py-0.5 border-transparent text-white", revenueLift >= 0 ? "bg-emerald-500" : "bg-amber-500")}>
                    {revenueLift >= 0 ? "+" : ""}{formatCurrency(revenueLift)}
                  </Badge>
                  <span className={cn("text-xs font-bold", revenueLift >= 0 ? "text-emerald-500" : "text-amber-500")}>
                    ({revenueLift >= 0 ? "+" : ""}{liftPct.toFixed(1)}%)
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Budget Response Curves Charts */}
      <Card className="shadow-sm border-border bg-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold tracking-tight">Media Channel Response Curves</CardTitle>
          <CardDescription className="text-xs">Diminishing returns curves representing spend vs forecasted revenue</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
          {/* Google Ads Curve */}
          <div className="space-y-2">
            <span className="text-sm font-semibold block text-center border-b border-border pb-1">Google Ads Curve</span>
            <div className="h-56">
              {googleCurve.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={googleCurve} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                    <XAxis dataKey="spend" tickFormatter={(v) => `$${v}`} style={{ fontSize: "9px" }} />
                    <YAxis tickFormatter={(v) => `$${v / 1000}k`} style={{ fontSize: "9px" }} />
                    <ChartTooltip
                      formatter={(v) => formatCurrency(Number(v))}
                      labelFormatter={(l) => `Spend: ${formatCurrency(Number(l))}`}
                      contentStyle={{ backgroundColor: "var(--popover)", borderColor: "var(--border)", fontSize: "10px" }}
                    />
                    <Line type="monotone" dataKey="revenue" stroke="var(--color-primary)" strokeWidth={2} dot={false} />
                    {simulation && (
                      <ReferenceDot
                        x={googleSim * (horizonSim / 30)}
                        y={
                          googleCurve.find((pt) => Math.abs(pt.spend - googleSim * (horizonSim / 30)) < 200)?.revenue ||
                          googleSim * 3.8 * (horizonSim / 30)
                        }
                        r={4}
                        fill="var(--color-primary)"
                        stroke="var(--background)"
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Skeleton className="h-full w-full bg-muted" />
              )}
            </div>
          </div>

          {/* Meta Ads Curve */}
          <div className="space-y-2">
            <span className="text-sm font-semibold block text-center border-b border-border pb-1">Meta Ads Curve</span>
            <div className="h-56">
              {metaCurve.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={metaCurve} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                    <XAxis dataKey="spend" tickFormatter={(v) => `$${v}`} style={{ fontSize: "9px" }} />
                    <YAxis tickFormatter={(v) => `$${v / 1000}k`} style={{ fontSize: "9px" }} />
                    <ChartTooltip
                      formatter={(v) => formatCurrency(Number(v))}
                      labelFormatter={(l) => `Spend: ${formatCurrency(Number(l))}`}
                      contentStyle={{ backgroundColor: "var(--popover)", borderColor: "var(--border)", fontSize: "10px" }}
                    />
                    <Line type="monotone" dataKey="revenue" stroke="oklch(0.556 0 0)" strokeWidth={2} dot={false} />
                    {simulation && (
                      <ReferenceDot
                        x={metaSim * (horizonSim / 30)}
                        y={
                          metaCurve.find((pt) => Math.abs(pt.spend - metaSim * (horizonSim / 30)) < 200)?.revenue ||
                          metaSim * 3.4 * (horizonSim / 30)
                        }
                        r={4}
                        fill="oklch(0.556 0 0)"
                        stroke="var(--background)"
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Skeleton className="h-full w-full bg-muted" />
              )}
            </div>
          </div>

          {/* Bing Ads Curve */}
          <div className="space-y-2">
            <span className="text-sm font-semibold block text-center border-b border-border pb-1">Bing Ads Curve</span>
            <div className="h-56">
              {bingCurve.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={bingCurve} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                    <XAxis dataKey="spend" tickFormatter={(v) => `$${v}`} style={{ fontSize: "9px" }} />
                    <YAxis tickFormatter={(v) => `$${v / 1000}k`} style={{ fontSize: "9px" }} />
                    <ChartTooltip
                      formatter={(v) => formatCurrency(Number(v))}
                      labelFormatter={(l) => `Spend: ${formatCurrency(Number(l))}`}
                      contentStyle={{ backgroundColor: "var(--popover)", borderColor: "var(--border)", fontSize: "10px" }}
                    />
                    <Line type="monotone" dataKey="revenue" stroke="oklch(0.708 0 0)" strokeWidth={2} dot={false} />
                    {simulation && (
                      <ReferenceDot
                        x={bingSim * (horizonSim / 30)}
                        y={
                          bingCurve.find((pt) => Math.abs(pt.spend - bingSim * (horizonSim / 30)) < 200)?.revenue ||
                          bingSim * 2.9 * (horizonSim / 30)
                        }
                        r={4}
                        fill="oklch(0.708 0 0)"
                        stroke="var(--background)"
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Skeleton className="h-full w-full bg-muted" />
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recommended allocation split */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="shadow-sm border-border bg-card">
          <CardHeader>
            <CardTitle className="text-base font-semibold tracking-tight">Current Budget Allocation</CardTitle>
            <CardDescription className="text-xs">Your active daily configuration split</CardDescription>
          </CardHeader>
          <CardContent className="h-56 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={currentAllocationData} layout="vertical" margin={{ left: 10, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
                <XAxis type="number" tickFormatter={(v) => `$${v}`} style={{ fontSize: "10px" }} />
                <YAxis dataKey="name" type="category" style={{ fontSize: "10px" }} />
                <ChartTooltip formatter={(v) => `$${Number(v).toLocaleString()}`} />
                <Bar dataKey="value" fill="var(--color-primary)" radius={[0, 4, 4, 0]}>
                  {currentAllocationData.map((entry, idx) => {
                    const color = idx === 0 ? "var(--color-primary)" : idx === 1 ? "oklch(0.556 0 0)" : "oklch(0.708 0 0)";
                    return <Cell key={`cell-${idx}`} fill={color} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-border bg-card">
          <CardHeader>
            <CardTitle className="text-base font-semibold tracking-tight">AI Recommended Optimal Split</CardTitle>
            <CardDescription className="text-xs">Calculated allocation split to maximize target ROAS and return volume</CardDescription>
          </CardHeader>
          <CardContent className="h-56 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={recommendedData} layout="vertical" margin={{ left: 10, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
                <XAxis type="number" tickFormatter={(v) => `$${v}`} style={{ fontSize: "10px" }} />
                <YAxis dataKey="name" type="category" style={{ fontSize: "10px" }} />
                <ChartTooltip formatter={(v) => `$${Number(v).toLocaleString()}`} />
                <Bar dataKey="value" fill="var(--color-primary)" radius={[0, 4, 4, 0]}>
                  {recommendedData.map((entry, idx) => {
                    const color = idx === 0 ? "var(--color-primary)" : idx === 1 ? "oklch(0.556 0 0)" : "oklch(0.708 0 0)";
                    return <Cell key={`cell-${idx}`} fill={color} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </motion.div>
  </>
);
}

function formatCurrency(val: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(val);
}
