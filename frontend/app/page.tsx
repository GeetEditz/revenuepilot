"use client";

import React, { useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  DollarSign,
  Percent,
  Calendar,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  Search,
  ExternalLink,
  Info,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  BarChart3,
  PieChart as PieIcon,
  Table as TableIcon
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal, Eye, Sliders, Brain } from "lucide-react";
import { ForecastRow } from "@/lib/api";
import { useForecast } from "@/lib/hooks/useQueries";
import {
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  PieChart,
  Pie,
  Legend
} from "recharts";

const containerVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      staggerChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

// Campaign static mock templates that scale based on selected revenue
const baseCampaigns = [
  { name: "PMax - Shopping Core", type: "Performance Max", revenueShare: 0.32, roas: 4.2, trend: "+12.4%" },
  { name: "Brand Search - Global", type: "Brand", revenueShare: 0.18, roas: 6.8, trend: "+2.1%" },
  { name: "Prospecting - Broad Match", type: "Prospecting", revenueShare: 0.14, roas: 2.8, trend: "-4.5%" },
  { name: "Remarketing - Dynamic Feed", type: "Remarketing", revenueShare: 0.12, roas: 4.9, trend: "+8.3%" },
  { name: "Search - High Intent Category", type: "Search", revenueShare: 0.11, roas: 3.5, trend: "+5.2%" },
  { name: "Demand Gen - Video Plus", type: "Demand Gen", revenueShare: 0.07, roas: 2.9, trend: "+15.0%" },
  { name: "Display - Audience Contextual", type: "Display", revenueShare: 0.06, roas: 1.8, trend: "-1.2%" },
];

function getCategoryOptimizationText(type: string): string {
  switch (type) {
    case "Performance Max":
      return "PMax scales dynamically across Search, Shopping, and Video. Maintain high-quality product feeds and negative lists to protect ROAS boundaries.";
    case "Brand":
      return "Brand campaigns capture high-intent users with organic baseline protection. Maintain impression share above 95% and monitor CPC inflation weekly.";
    case "Prospecting":
      return "Prospecting targets new customer acquisition. Use broad match with smart bidding caps to capture volume while filtering low-value queries.";
    case "Remarketing":
      return "Remarketing captures warm audiences. Use dynamic asset feeds and segment by historical intent depth (cart abandons vs page views) to maximize returns.";
    case "Search":
      return "High-intent generic search captures active category demand. Keep ad relevance high, optimize landing pages, and refine match types regularly.";
    case "Demand Gen":
      return "Demand Gen drives visual consideration across YouTube and Gmail. Focus on high-CTR video overlays and custom lookalike audience segments.";
    case "Display":
      return "Display builds awareness and retargeting touchpoints. Clean out placement exclusions monthly to avoid wasted ad spend on low-tier mobile apps.";
    default:
      return "This campaign is configured to scale dynamically across channels. Maintain baseline performance limits by preserving keyword targeting boundaries.";
  }
}

function getTrajectoryExplanation(trend: string): string {
  const isPositive = !trend.startsWith("-");
  if (isPositive) {
    return `Upward momentum of ${trend} indicates expansion headroom. Ideal time to scale budget limits or relax bidding targets to capture volume.`;
  } else {
    return `Recent softening of ${trend} signals volume saturation or seasonal contraction. Consider tightening bid caps to preserve efficiency.`;
  }
}

export default function ExecutiveDashboard() {
  const { data: forecastData, isLoading } = useForecast();
  const data = forecastData ?? [];
  const [expandedCampaign, setExpandedCampaign] = useState<string | null>(null);
  const [horizon, setHorizon] = useState<30 | 60 | 90>(30);

  if (isLoading && data.length === 0) {
    return <DashboardSkeleton />;
  }

  if (data.length === 0) {
    return <DashboardSkeleton />;
  }

  // Slice based on horizon
  const activeData = data.slice(0, horizon);

  // Aggregated calculations for current view
  const lastRow = activeData[activeData.length - 1];
  const totalRevenueP50 = lastRow.Revenue_P50;
  const totalRevenueP10 = lastRow.Revenue_P10;
  const totalRevenueP90 = lastRow.Revenue_P90;
  const avgROASP50 = activeData.reduce((sum, r) => sum + r.ROAS_P50, 0) / activeData.length;
  const avgConfidence = activeData.reduce((sum, r) => sum + r.Confidence_Score, 0) / activeData.length;

  // Channel calculations for the end of the horizon
  const googleRev = lastRow.Google_Revenue;
  const metaRev = lastRow.Meta_Revenue;
  const bingRev = lastRow.Bing_Revenue;
  const totalChanRev = googleRev + metaRev + bingRev;

  // Let's assume spend shares based on historical trends
  const googleSpend = googleRev / lastRow.Google_ROAS;
  const metaSpend = metaRev / lastRow.Meta_ROAS;
  const bingSpend = bingRev / lastRow.Bing_ROAS;
  const totalSpend = googleSpend + metaSpend + bingSpend;

  const channelsData = [
    {
      name: "Google Ads",
      revenue: googleRev,
      roas: lastRow.Google_ROAS,
      spendShare: Math.round((googleSpend / totalSpend) * 100),
      contribution: Math.round((googleRev / totalChanRev) * 100),
      color: "hsl(var(--primary))",
    },
    {
      name: "Meta Ads",
      revenue: metaRev,
      roas: lastRow.Meta_ROAS,
      spendShare: Math.round((metaSpend / totalSpend) * 100),
      contribution: Math.round((metaRev / totalChanRev) * 100),
      color: "oklch(0.556 0 0)",
    },
    {
      name: "Bing Ads",
      revenue: bingRev,
      roas: lastRow.Bing_ROAS,
      spendShare: Math.round((bingSpend / totalSpend) * 100),
      contribution: Math.round((bingRev / totalChanRev) * 100),
      color: "oklch(0.708 0 0)",
    },
  ];

  // Dynamic campaign rows derived from total revenue
  const campaigns = baseCampaigns.map((c) => {
    const rev = totalRevenueP50 * c.revenueShare;
    const low = lowBound(rev, 0.15);
    const high = highBound(rev, 0.15);
    return {
      ...c,
      revenue: rev,
      lowRange: low,
      highRange: high,
    };
  });

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8"
    >
      {/* Hero Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            RevenuePilot AI
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            AI-Assisted Probabilistic Revenue Forecasting for Ecommerce Marketing Agencies
          </p>
        </div>
        <div className="flex items-center gap-2 self-start md:self-auto">
          <span className="text-xs text-muted-foreground font-medium mr-1">Forecast Horizon:</span>
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

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* KPI 1: Revenue Forecast (P50) */}
        <Card className="border-2 border-primary bg-card relative overflow-hidden shadow-md transition-all duration-300 hover:shadow-primary/5">
          <div className="absolute top-0 right-0 p-2 opacity-5">
            <DollarSign className="h-20 w-20 text-primary" />
          </div>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Revenue Forecast (P50)
            </CardTitle>
            <Badge className="bg-primary text-primary-foreground text-[9px] font-bold px-1.5 py-0.5 border-transparent">Median</Badge>
          </CardHeader>
          <CardContent className="relative z-10">
            <div className="text-3xl font-extrabold tracking-tight text-foreground">{formatCurrency(totalRevenueP50)}</div>
            <p className="text-[10px] text-emerald-500 font-semibold flex items-center gap-1 mt-1.5">
              <TrendingUp className="h-3.5 w-3.5 shrink-0" />
              <span>Expected Target Target</span>
            </p>
          </CardContent>
        </Card>

        {/* KPI 2: Confidence Range (P10 - P90) */}
        <Card className="shadow-sm border-border bg-card transition-all duration-300 hover:border-muted-foreground/30">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Confidence Range
            </CardTitle>
            <Badge variant="outline" className="text-[9px] font-medium border-border">P10 - P90</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold tracking-tight text-foreground whitespace-nowrap mt-0.5">
              {formatCurrency(totalRevenueP10)} - {formatCurrency(totalRevenueP90)}
            </div>
            <p className="text-[10px] text-muted-foreground mt-2 font-medium">
              80% probability envelope
            </p>
          </CardContent>
        </Card>

        {/* KPI 3: Expected ROAS */}
        <Card className="shadow-sm border-border bg-card transition-all duration-300 hover:border-muted-foreground/30">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Expected ROAS
            </CardTitle>
            <Badge variant="outline" className="text-[9px] text-emerald-500 bg-emerald-500/5 border-emerald-500/20 font-bold">Optimal</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold tracking-tight text-foreground">{avgROASP50.toFixed(2)}x</div>
            <p className="text-[10px] text-emerald-500 font-semibold flex items-center gap-1 mt-1.5">
              <TrendingUp className="h-3.5 w-3.5 shrink-0" />
              <span>Blended efficiency target</span>
            </p>
          </CardContent>
        </Card>

        {/* KPI 4: Confidence Score */}
        <Card className="shadow-sm border-border bg-card transition-all duration-300 hover:border-muted-foreground/30">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Confidence Score
            </CardTitle>
            <Info className="h-4 w-4 text-primary opacity-60" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold tracking-tight text-foreground">{Math.round(avgConfidence * 100)}%</div>
            <div className="mt-2.5">
              <Progress value={avgConfidence * 100} className="h-1 bg-secondary" />
            </div>
          </CardContent>
        </Card>

        {/* KPI 5: Forecast Horizon */}
        <Card className="shadow-sm border-border bg-card transition-all duration-300 hover:border-muted-foreground/30">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Forecast Horizon
            </CardTitle>
            <Calendar className="h-4 w-4 text-primary opacity-60" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold tracking-tight text-foreground">{horizon} Days</div>
            <p className="text-[10px] text-muted-foreground mt-2.5 font-medium">
              Until end of active period
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Page Content: Charts & Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Forecast chart: span 2 */}
        <Card className="lg:col-span-2 shadow-sm border-border bg-card">
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <div>
              <CardTitle className="text-lg font-semibold tracking-tight">Probabilistic Revenue Forecast</CardTitle>
              <CardDescription className="text-xs">Cumulative forecasting bands showing P10 (Low-risk), P50 (Expected), and P90 (High-performance) limits</CardDescription>
            </div>
            <Badge variant="outline" className="text-xs font-medium border-border">
              Cumulative USD
            </Badge>
          </CardHeader>
          <CardContent className="h-80 w-full pr-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={activeData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorP50" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.15}/>
                    <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorInterval" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.05}/>
                    <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0.01}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                <XAxis
                  dataKey="Forecast_Horizon"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  style={{ fontSize: "11px", fill: "var(--color-muted-foreground)" }}
                  tickFormatter={(val) => `Day ${val}`}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  style={{ fontSize: "11px", fill: "var(--color-muted-foreground)" }}
                  tickFormatter={(val) => `$${(val / 1000).toFixed(0)}k`}
                />
                <ChartTooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const row = payload[0].payload as ForecastRow;
                      return (
                        <div className="bg-popover border border-border rounded-lg shadow-md p-3 text-popover-foreground text-xs space-y-1.5">
                          <p className="font-semibold border-b border-border pb-1">Day {row.Forecast_Horizon} Forecast</p>
                          <div className="flex justify-between gap-6">
                            <span className="text-muted-foreground">P90 (Optimistic):</span>
                            <span className="font-bold">{formatCurrency(row.Revenue_P90)}</span>
                          </div>
                          <div className="flex justify-between gap-6">
                            <span className="font-medium text-primary">P50 (Expected):</span>
                            <span className="font-bold text-primary">{formatCurrency(row.Revenue_P50)}</span>
                          </div>
                          <div className="flex justify-between gap-6 border-b border-border pb-1">
                            <span className="text-muted-foreground">P10 (Conservative):</span>
                            <span className="font-bold">{formatCurrency(row.Revenue_P10)}</span>
                          </div>
                          <div className="flex justify-between gap-6">
                            <span className="text-muted-foreground">Confidence Score:</span>
                            <span className="font-bold text-foreground">{Math.round(row.Confidence_Score * 100)}%</span>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                {/* Confidence Interval band */}
                <Area
                  type="monotone"
                  dataKey="Revenue_P90"
                  stroke="none"
                  fill="url(#colorInterval)"
                  id="p90-area"
                />
                <Area
                  type="monotone"
                  dataKey="Revenue_P10"
                  stroke="none"
                  fill="var(--background)"
                  id="p10-area"
                />
                {/* Dashed boundary lines for intervals */}
                <Line
                  type="monotone"
                  dataKey="Revenue_P90"
                  stroke="var(--color-primary)"
                  strokeWidth={1}
                  strokeDasharray="4 4"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="Revenue_P10"
                  stroke="var(--color-primary)"
                  strokeWidth={1}
                  strokeDasharray="4 4"
                  dot={false}
                />
                {/* Expected Line */}
                <Area
                  type="monotone"
                  dataKey="Revenue_P50"
                  stroke="var(--color-primary)"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#colorP50)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Channel Performance Share Cards: span 1 */}
        <Card className="shadow-sm border-border bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-semibold tracking-tight">Channel Share</CardTitle>
            <CardDescription className="text-xs">Relative contribution to total predicted revenue</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center h-[280px]">
            <ResponsiveContainer width="100%" height="70%">
              <PieChart>
                <Pie
                  data={channelsData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={4}
                  dataKey="revenue"
                >
                  {channelsData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <ChartTooltip
                  formatter={(value) => formatCurrency(Number(value))}
                  contentStyle={{
                    backgroundColor: "var(--popover)",
                    borderColor: "var(--border)",
                    fontSize: "11px",
                    borderRadius: "8px",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="grid grid-cols-3 w-full gap-2 text-center text-xs mt-3 border-t border-border pt-3">
              {channelsData.map((ch) => (
                <div key={ch.name} className="space-y-0.5">
                  <div className="flex items-center justify-center gap-1.5 font-medium text-muted-foreground">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: ch.color }} />
                    <span>{ch.name.split(" ")[0]}</span>
                  </div>
                  <div className="font-bold text-sm">{ch.contribution}%</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Channel Performance Metrics Table */}
      <Card className="shadow-sm border-border bg-card">
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <CardTitle className="text-lg font-semibold tracking-tight">Channel Performance Metrics</CardTitle>
              <CardDescription className="text-xs">Individual advertising platform contribution and budget utilization forecasting</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Channel Source</TableHead>
                <TableHead className="text-right">Predicted Revenue</TableHead>
                <TableHead className="text-right">Projected ROAS</TableHead>
                <TableHead className="text-right">Budget Share %</TableHead>
                <TableHead className="text-right">Revenue Contribution %</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {channelsData.map((ch) => (
                <TableRow key={ch.name} className="hover:bg-muted/40 transition-colors">
                  <TableCell className="font-semibold flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: ch.color }} />
                    {ch.name}
                  </TableCell>
                  <TableCell className="text-right font-bold">{formatCurrency(ch.revenue)}</TableCell>
                  <TableCell className="text-right font-medium text-primary">{ch.roas.toFixed(2)}x</TableCell>
                  <TableCell className="text-right">{ch.spendShare}%</TableCell>
                  <TableCell className="text-right font-semibold">{ch.contribution}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Campaign Performance Detail Cards */}
      <Card className="shadow-sm border-border bg-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold tracking-tight">Campaign Category Performance</CardTitle>
          <CardDescription className="text-xs">Detailed drill-down across standard commercial campaigns with confidence intervals</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Campaign Category</TableHead>
                <TableHead>Strategy Type</TableHead>
                <TableHead className="text-right">Est. Revenue (P50)</TableHead>
                <TableHead className="text-right">Forecast Range (P10 - P90)</TableHead>
                <TableHead className="text-right">Target ROAS</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {campaigns.map((c) => (
                <React.Fragment key={c.name}>
                  <TableRow
                    className="hover:bg-muted/40 transition-colors cursor-pointer group"
                    onClick={() => setExpandedCampaign(expandedCampaign === c.name ? null : c.name)}
                  >
                    <TableCell className="font-semibold group-hover:text-primary transition-colors">{c.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[10px] py-0 px-2 font-medium">
                        {c.type}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-bold">{formatCurrency(c.revenue)}</TableCell>
                    <TableCell className="text-right text-xs text-muted-foreground font-medium">
                      {formatCurrency(c.lowRange)} - {formatCurrency(c.highRange)}
                    </TableCell>
                    <TableCell className="text-right font-semibold text-primary">{c.roas.toFixed(2)}x</TableCell>
                    <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-8 w-8 text-muted-foreground hover:text-foreground"
                          onClick={() => setExpandedCampaign(expandedCampaign === c.name ? null : c.name)}
                        >
                          {expandedCampaign === c.name ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        </Button>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                              <span className="sr-only">Open menu</span>
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-48 bg-popover border-border">
                            <DropdownMenuLabel className="text-xs">Campaign Actions</DropdownMenuLabel>
                            <DropdownMenuSeparator className="bg-border" />
                            <DropdownMenuItem onClick={() => setExpandedCampaign(expandedCampaign === c.name ? null : c.name)}>
                              <Eye className="mr-2 h-3.5 w-3.5 opacity-70" />
                              <span className="text-xs">{expandedCampaign === c.name ? "Hide Details" : "Show Details"}</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => window.location.href = `/simulator?channel=${c.name.includes("PMax") || c.name.includes("Search") ? "Google" : c.name.includes("Remarketing") || c.name.includes("Prospecting") ? "Meta" : "Bing"}`}>
                              <Sliders className="mr-2 h-3.5 w-3.5 opacity-70" />
                              <span className="text-xs">Optimize Budget</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => window.location.href = "/insights"}>
                              <Brain className="mr-2 h-3.5 w-3.5 opacity-70" />
                              <span className="text-xs">View Insights</span>
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </TableCell>
                  </TableRow>
                  {expandedCampaign === c.name && (
                    <TableRow className="bg-muted/10 hover:bg-muted/10">
                      <TableCell colSpan={6} className="p-4 border-t border-b border-border/60 whitespace-normal">
                        <motion.div
                          initial={{ opacity: 0, y: -4 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="border border-border/80 rounded-xl p-5 bg-card/60 backdrop-blur-sm shadow-sm space-y-4"
                        >
                          <div className="flex items-center justify-between border-b border-border/50 pb-3">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                              <h4 className="text-xs font-bold tracking-tight text-foreground uppercase tracking-wider">
                                Tactical Recommendation Details
                              </h4>
                            </div>
                            <Button 
                              variant="outline" 
                              size="sm" 
                              className="text-xs h-7 px-2.5 font-medium border-border"
                              onClick={() => window.location.href = `/simulator?channel=${c.name.includes("PMax") || c.name.includes("Search") ? "Google" : c.name.includes("Remarketing") || c.name.includes("Prospecting") ? "Meta" : "Bing"}`}
                            >
                              <Sliders className="h-3 w-3 mr-1.5 text-primary" />
                              Tune Budget Model
                            </Button>
                          </div>
                           <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                            <div className="space-y-1.5 p-3.5 rounded-lg bg-muted/20 border border-border/30">
                              <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-bold uppercase tracking-wider">
                                <Brain className="h-3.5 w-3.5 text-primary" />
                                <span>Category Optimization</span>
                              </div>
                              <p className="text-xs text-foreground leading-relaxed font-medium">
                                {getCategoryOptimizationText(c.type)}
                              </p>
                            </div>
                            <div className="space-y-1.5 p-3.5 rounded-lg bg-muted/20 border border-border/30">
                              <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-bold uppercase tracking-wider">
                                <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
                                <span>Performance Trajectory</span>
                              </div>
                              <div className="flex items-baseline gap-2 mt-1">
                                <span className="text-xl font-extrabold text-emerald-500 tracking-tight">{c.trend}</span>
                                <span className="text-xs text-muted-foreground">relative weekly change</span>
                              </div>
                              <p className="text-[10px] text-muted-foreground leading-snug">
                                {getTrajectoryExplanation(c.trend)}
                              </p>
                            </div>
                            <div className="space-y-1.5 p-3.5 rounded-lg bg-muted/20 border border-border/30">
                              <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-bold uppercase tracking-wider">
                                <Sliders className="h-3.5 w-3.5 text-primary" />
                                <span>Budget Share Recommendation</span>
                              </div>
                              <div className="flex items-baseline gap-2 mt-1">
                                <span className="text-xl font-extrabold text-foreground tracking-tight">{(c.revenueShare * 100).toFixed(0)}%</span>
                                <span className="text-xs text-muted-foreground">allocated share limit</span>
                              </div>
                              <p className="text-[10px] text-muted-foreground leading-snug">
                                Target contribution share designed to preserve blended ROAS boundaries for {c.name.split(" ")[0]} targets.
                              </p>
                            </div>
                          </div>
                        </motion.div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// Subordinate helper calculations
function formatCurrency(val: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(val);
}

function lowBound(val: number, multiplier: number) {
  return Math.round(val * (1 - multiplier));
}

function highBound(val: number, multiplier: number) {
  return Math.round(val * (1 + multiplier));
}

function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <Skeleton className="h-10 w-96 bg-muted" />
        <Skeleton className="h-4 w-72 bg-muted" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-lg bg-muted" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Skeleton className="lg:col-span-2 h-80 rounded-lg bg-muted" />
        <Skeleton className="h-80 rounded-lg bg-muted" />
      </div>
      <Skeleton className="h-60 rounded-lg bg-muted" />
    </div>
  );
}
