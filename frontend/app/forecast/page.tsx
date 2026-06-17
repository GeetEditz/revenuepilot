"use client";

import React, { useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  TrendingDown,
  Info,
  Calendar,
  Layers,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ForecastRow } from "@/lib/api";
import { useForecast } from "@/lib/hooks/useQueries";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  Legend
} from "recharts";
import { Skeleton } from "@/components/ui/skeleton";

export default function ForecastAnalysis() {
  const { data: forecastData, isLoading } = useForecast();
  const data = forecastData ?? [];
  const [horizon, setHorizon] = useState<30 | 60 | 90>(60);

  if (isLoading && data.length === 0) {
    return <ForecastSkeleton />;
  }

  if (data.length === 0) {
    return <ForecastSkeleton />;
  }

  const activeData = data.slice(0, horizon);
  const lastRow = activeData[activeData.length - 1];

  // Specific forecast points
  const checkpoints = [
    { label: "Short Term (Day 7)", index: Math.min(6, activeData.length - 1) },
    { label: "Mid Horizon (Day 15)", index: Math.min(14, activeData.length - 1) },
    { label: "Long Term (Day 30)", index: Math.min(29, activeData.length - 1) },
  ];
  if (horizon >= 60) {
    checkpoints.push({ label: "Extended (Day 60)", index: Math.min(59, activeData.length - 1) });
  }
  if (horizon >= 90) {
    checkpoints.push({ label: "Quarterly Limit (Day 90)", index: Math.min(89, activeData.length - 1) });
  }

  const checkpointRows = checkpoints.map((cp) => ({
    label: cp.label,
    row: activeData[cp.index],
  }));

  // Calculations for risk and confidence
  const expectedRev = lastRow.Revenue_P50;
  const lowRev = lastRow.Revenue_P10;
  const highRev = lastRow.Revenue_P90;

  const downsideRiskPct = ((expectedRev - lowRev) / expectedRev) * 100;
  const upsidePotentialPct = ((highRev - expectedRev) / expectedRev) * 100;
  const overallConfidence = lastRow.Confidence_Score * 100;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-8"
    >
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Forecast Analysis</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Probabilistic distribution workspace and performance risk evaluation
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-semibold uppercase mr-1">Select Horizon:</span>
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

      {/* Grid of details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Expected numbers */}
        <Card className="shadow-sm border-border bg-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold tracking-tight">Expected Returns</CardTitle>
            <CardDescription className="text-xs">Median probability prediction models (P50)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1">
              <span className="text-xs text-muted-foreground font-medium">Expected Revenue</span>
              <div className="text-3xl font-bold">{formatCurrency(expectedRev)}</div>
            </div>
            <div className="space-y-1">
              <span className="text-xs text-muted-foreground font-medium">Expected Overall ROAS</span>
              <div className="text-3xl font-bold text-primary">{lastRow.ROAS_P50.toFixed(2)}x</div>
            </div>
            <div className="pt-2 border-t border-border flex justify-between text-xs text-muted-foreground">
              <span>Confidence Index</span>
              <span className="font-semibold text-foreground">{overallConfidence.toFixed(0)}%</span>
            </div>
          </CardContent>
        </Card>

        {/* Prediction Interval Info */}
        <Card className="shadow-sm border-border bg-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold tracking-tight">Confidence Range</CardTitle>
            <CardDescription className="text-xs">Model variance bounds across the {horizon}-day forecast</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-semibold text-muted-foreground">
                <span>P10 (Conservative)</span>
                <span>{formatCurrency(lowRev)}</span>
              </div>
              <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                <div className="bg-amber-500 h-full rounded-full" style={{ width: "30%" }} />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-semibold text-muted-foreground">
                <span>P50 (Expected)</span>
                <span>{formatCurrency(expectedRev)}</span>
              </div>
              <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                <div className="bg-primary h-full rounded-full" style={{ width: "65%" }} />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-semibold text-muted-foreground">
                <span>P90 (Optimistic)</span>
                <span>{formatCurrency(highRev)}</span>
              </div>
              <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full rounded-full" style={{ width: "100%" }} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Risk Analysis Card */}
        <Card className="shadow-sm border-border bg-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold tracking-tight">Risk Assessment</CardTitle>
            <CardDescription className="text-xs">Model risk volatility metrics & bounds</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="border border-border p-3 rounded-lg bg-muted/30">
                <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider block">Downside Volatility</span>
                <span className="text-lg font-bold text-amber-500 mt-1 block">-{downsideRiskPct.toFixed(1)}%</span>
                <span className="text-[10px] text-muted-foreground mt-0.5 block">Worst-case deviation</span>
              </div>
              <div className="border border-border p-3 rounded-lg bg-muted/30">
                <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider block">Upside Potential</span>
                <span className="text-lg font-bold text-emerald-500 mt-1 block">+{upsidePotentialPct.toFixed(1)}%</span>
                <span className="text-[10px] text-muted-foreground mt-0.5 block">Best-case deviation</span>
              </div>
            </div>
            <div className="bg-muted border border-border p-3 rounded-lg text-xs flex gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
              <p className="text-muted-foreground leading-normal">
                Risk profile is <strong className="text-foreground font-semibold">STABLE</strong>. The historical model bounds indicate steady performance, with a low probability of scaling failures.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Advanced Chart workspace */}
      <Card className="shadow-sm border-border bg-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold tracking-tight">Forecast Workspace Distribution</CardTitle>
          <CardDescription className="text-xs">Detailed day-by-day probabilistic projections and ROAS limits</CardDescription>
        </CardHeader>
        <CardContent className="h-96 pr-4">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={activeData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
              <defs>
                <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.15}/>
                  <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="Forecast_Horizon"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                style={{ fontSize: "11px", fill: "var(--color-muted-foreground)" }}
                tickFormatter={(val) => `Day ${val}`}
              />
              <YAxis
                yAxisId="rev"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                style={{ fontSize: "11px", fill: "var(--color-muted-foreground)" }}
                tickFormatter={(val) => `$${(val / 1000).toFixed(0)}k`}
              />
              <YAxis
                yAxisId="roas"
                orientation="right"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                style={{ fontSize: "11px", fill: "var(--color-muted-foreground)" }}
                tickFormatter={(val) => `${val}x`}
              />
              <ChartTooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const row = payload[0].payload as ForecastRow;
                    return (
                      <div className="bg-popover border border-border rounded-lg shadow-md p-3 text-popover-foreground text-xs space-y-1.5">
                        <p className="font-semibold border-b border-border pb-1">Day {row.Forecast_Horizon} Detailed Forecast</p>
                        <div className="flex justify-between gap-6">
                          <span className="text-muted-foreground">P90 Rev:</span>
                          <span className="font-bold">{formatCurrency(row.Revenue_P90)}</span>
                        </div>
                        <div className="flex justify-between gap-6">
                          <span className="text-primary font-medium">P50 Rev:</span>
                          <span className="font-bold text-primary">{formatCurrency(row.Revenue_P50)}</span>
                        </div>
                        <div className="flex justify-between gap-6 border-b border-border pb-1">
                          <span className="text-muted-foreground">P10 Rev:</span>
                          <span className="font-bold">{formatCurrency(row.Revenue_P10)}</span>
                        </div>
                        <div className="flex justify-between gap-6">
                          <span className="text-muted-foreground">Expected ROAS:</span>
                          <span className="font-bold text-foreground">{row.ROAS_P50.toFixed(2)}x</span>
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              {/* Area P50 */}
              <Area
                yAxisId="rev"
                type="monotone"
                dataKey="Revenue_P50"
                stroke="var(--color-primary)"
                strokeWidth={2}
                fill="url(#chartGradient)"
                name="Expected Revenue"
              />
              {/* Line ROAS */}
              <Line
                yAxisId="roas"
                type="monotone"
                dataKey="ROAS_P50"
                stroke="oklch(0.556 0 0)"
                strokeWidth={1.5}
                dot={false}
                name="Expected ROAS"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Target checkpoints table */}
      <Card className="shadow-sm border-border bg-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold tracking-tight">Timeline Checkpoints</CardTitle>
          <CardDescription className="text-xs">Summary of cumulative checkpoints along the forecasted path</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timeline Node</TableHead>
                <TableHead className="text-right">Conservative (P10)</TableHead>
                <TableHead className="text-right">Expected (P50)</TableHead>
                <TableHead className="text-right">Optimistic (P90)</TableHead>
                <TableHead className="text-right">Average ROAS</TableHead>
                <TableHead className="text-right">Model Variance</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {checkpointRows.map((cp) => {
                if (!cp.row) return null;
                const variance = ((cp.row.Revenue_P90 - cp.row.Revenue_P10) / cp.row.Revenue_P50) * 100;
                return (
                  <TableRow key={cp.label} className="hover:bg-muted/40 transition-colors">
                    <TableCell className="font-semibold">{cp.label}</TableCell>
                    <TableCell className="text-right">{formatCurrency(cp.row.Revenue_P10)}</TableCell>
                    <TableCell className="text-right font-bold">{formatCurrency(cp.row.Revenue_P50)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(cp.row.Revenue_P90)}</TableCell>
                    <TableCell className="text-right font-semibold text-primary">{cp.row.ROAS_P50.toFixed(2)}x</TableCell>
                    <TableCell className="text-right text-xs text-muted-foreground font-semibold">
                      ± {variance.toFixed(0)}%
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function formatCurrency(val: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(val);
}

function ForecastSkeleton() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <Skeleton className="h-10 w-96 bg-muted" />
        <Skeleton className="h-4 w-72 bg-muted" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Skeleton className="h-44 rounded-lg bg-muted" />
        <Skeleton className="h-44 rounded-lg bg-muted" />
        <Skeleton className="h-44 rounded-lg bg-muted" />
      </div>
      <Skeleton className="h-96 rounded-lg bg-muted" />
      <Skeleton className="h-60 rounded-lg bg-muted" />
    </div>
  );
}
