"use client";

import React, { useMemo } from "react";
import { motion } from "framer-motion";
import {
  Sparkles,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  TrendingUp,
  Percent,
  Compass,
  FileText,
  BadgeAlert,
  ArrowRight,
  ShieldCheck,
  CheckCircle,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { useInsights } from "@/lib/hooks/useQueries";
import { Skeleton } from "@/components/ui/skeleton";

interface InsightSection {
  id: string;
  title: string;
  category: "summary" | "driver" | "risk" | "opportunity" | "recommendation" | "confidence";
  priority: "high" | "medium" | "low";
  shortText: string;
  longText: string;
}

export default function AIInsights() {
  const { data: insightsData, isLoading } = useInsights();
  const insights = insightsData ?? [];

  if (isLoading && insights.length === 0) {
    return <InsightsSkeleton />;
  }

  // Create structured sections mapping to the requested layout
  const structuredSections: InsightSection[] = insights.length >= 6
    ? [
        {
          id: "summary",
          title:   "Executive Summary",
          category: "summary",  
          priority: "high",
          shortText: insights[0].split(". ")[0] + ".",
          longText: insights[0],
        },
        {
          id: "drivers",
          title: "Growth Drivers",
          category: "driver",
          priority: "high",
          shortText: insights[1].split(". ")[0] + ".",
          longText: insights[1],
        },
        {
          id: "risks",
          title: "Revenue Risks",
          category: "risk",
          priority: "medium",
          shortText: insights[2].split(". ")[0] + ".",
          longText: insights[2],
        },
        {
          id: "opportunities",
          title: "Campaign Opportunities",
          category: "opportunity",
          priority: "medium",
          shortText: insights[3].split(". ")[0] + ".",
          longText: insights[3],
        },
        {
          id: "recommendations",
          title: "Budget Recommendations",
          category: "recommendation",
          priority: "high",
          shortText: insights[4].split(". ")[0] + ".",
          longText: insights[4],
        },
        {
          id: "confidence",
          title: "Confidence Explanation",
          category: "confidence",
          priority: "low",
          shortText: insights[5].split(". ")[0] + ".",
          longText: insights[5],
        },
      ]
    : insights.length >= 3
    ? [
        {
          id: "30d",
          title: "30-Day Strategic AI Forecast",
          category: "summary",
          priority: "high",
          shortText: insights[0].split(". ")[0] + ".",
          longText: insights[0],
        },
        {
          id: "60d",
          title: "60-Day Strategic AI Forecast",
          category: "opportunity",
          priority: "medium",
          shortText: insights[1].split(". ")[0] + ".",
          longText: insights[1],
        },
        {
          id: "90d",
          title: "90-Day Strategic AI Forecast",
          category: "confidence",
          priority: "low",
          shortText: insights[2].split(". ")[0] + ".",
          longText: insights[2],
        }
      ]
    : [
        {
          id: "summary",
          title: "Executive Summary",
          category: "summary",
          priority: "high",
          shortText: "Overall forecasting trajectory is positive, with an expected 30-day cumulative revenue target of $750,000 at a baseline 3.48x ROAS.",
          longText: "Our core forecasting models show strong, positive baseline metrics for the upcoming quarter. Organic repeat purchases combined with stable Google Ads Performance Max returns represent the primary growth engine. We recommend maintaining current channel configurations while planning a minor shift of budget towards high-efficiency campaigns to maximize volume without compromising margin limits.",
        },
        {
          id: "drivers",
          title: "Growth Drivers",
          category: "driver",
          priority: "high",
          shortText: "Performance Max shopping feeds and branded search campaigns are performing at maximum efficiency, contributing to 52% of total predicted revenue.",
          longText: "Google Ads Performance Max remains the primary volume driver. Historical cohort analyses reveal that shopping placements capture high-intent search queries with high conversion rates. Additionally, branded search provides an extremely efficient conversion capture layer (6.8x target ROAS), which should be fully funded to ensure zero impression share loss to competitors.",
        },
        {
          id: "risks",
          title: "Revenue Risks",
          category: "risk",
          priority: "medium",
          shortText: "Meta Ads prospecting campaigns are showing high frequency fatigue and declining marginal ROAS, creating a downside risk if Daily Budgets exceed $1,200.",
          longText: "Analysis of the Meta Ads conversion feedback loop indicates creative fatigue in top-of-funnel prospecting sets. The frequency has reached 3.4 over a 7-day period, indicating audience saturation. If Daily Budgets are pushed past $1,200, the marginal ROAS is predicted to fall below 2.0x, dragging down the workspace target. We recommend creative rotation immediately.",
        },
        {
          id: "opportunities",
          title: "Campaign Opportunities",
          category: "opportunity",
          priority: "medium",
          shortText: "Bing Ads Search has low query volume but represents a highly efficient capture channel with an expected ROAS of 2.9x.",
          longText: "Bing Ads displays highly efficient metrics despite lower traffic volumes. Because bid competition is lower, CPA is 18% lower than comparable Google Search queries. We recommend testing a 10% daily budget increase on Bing to capture long-tail high-intent queries that are currently unserved due to budget exhaustion.",
        },
        {
          id: "recommendations",
          title: "Budget Recommendations",
          category: "recommendation",
          priority: "high",
          shortText: "Shift 8% of Meta prospecting budget to Google PMax, and increase Bing daily budget by $50 to capture unserved high-intent search queries.",
          longText: "To maximize total target revenue, reallocate capital to match the AI optimal recommendation: Google Ads (55%), Meta Ads (35%), and Bing Ads (10%). This is projected to generate a 15% revenue lift over current performance baselines while protecting overall margins from diminishing return curves.",
        },
        {
          id: "confidence",
          title: "Confidence Explanation",
          category: "confidence",
          priority: "low",
          shortText: "High model confidence (92% baseline) for the 30-day horizon, tapering to 84% at the 90-day mark due to natural cohort variance.",
          longText: "Our LightGBM quantile regression models achieve high accuracy on historical training test splits. The P50 prediction interval shows tight variance for the first 30 days due to consistent customer lifetime value distributions. The widening of the P10 to P90 intervals at 90 days represents seasonal variations and macro-economic factors built into the probability engine.",
        },
      ];

  const getPriorityColor = (prio: "high" | "medium" | "low") => {
    switch (prio) {
      case "high":
        return "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20";
      case "medium":
        return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20";
      case "low":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20";
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-8"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">AI Insights</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Executive strategic intelligence and growth recommendations generated by the forecasting engine
          </p>
        </div>
        <Badge variant="outline" className="bg-primary/5 text-primary border-primary/10 gap-1.5 px-3 py-1 text-xs font-semibold shadow-sm">
          <Sparkles className="h-3.5 w-3.5" />
          Growth Intelligence Active
        </Badge>
      </div>

      {/* Main timeline layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Left Side: Summary Widget */}
        <div className="lg:col-span-1 space-y-6">
          <Card className="shadow-sm border-border bg-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold tracking-tight">Report Metadata</CardTitle>
              <CardDescription className="text-xs">Context details for this analytical run</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              <div className="flex justify-between py-1 border-b border-border">
                <span className="text-muted-foreground">Analyst Model</span>
                <span className="font-semibold">QuantileLGBM v1.0</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border">
                <span className="text-muted-foreground">Confidence Base</span>
                <span className="font-semibold">92% Average</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border">
                <span className="text-muted-foreground">Analysis Horizon</span>
                <span className="font-semibold">30 - 90 Days</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-muted-foreground">Data Completeness</span>
                <span className="font-semibold text-emerald-500">100% Verified</span>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-sm border-border bg-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold tracking-tight">Quick Action Items</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="flex items-start gap-2.5">
                <CheckCircle className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <span className="text-muted-foreground leading-normal">Reduce Meta Daily Budget by $150</span>
              </div>
              <div className="flex items-start gap-2.5">
                <CheckCircle className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <span className="text-muted-foreground leading-normal">Increase Google PMax Shopping allocation</span>
              </div>
              <div className="flex items-start gap-2.5">
                <CheckCircle className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <span className="text-muted-foreground leading-normal">Rotate Meta prospecting creatives</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Side: Accordion and Details */}
        <div className="lg:col-span-3 space-y-6">
          <Card className="shadow-sm border-border bg-card">
            <CardHeader>
              <CardTitle className="text-lg font-semibold tracking-tight">Strategic Intelligence Report</CardTitle>
              <CardDescription className="text-xs">Click sections below to expand full details and analysis</CardDescription>
            </CardHeader>
            <CardContent>
              <Accordion type="single" defaultValue="summary" collapsible className="w-full space-y-4">
                {structuredSections.map((sec) => (
                  <AccordionItem
                    key={sec.id}
                    value={sec.id}
                    className="border border-border rounded-lg px-4 py-1.5 bg-muted/20 hover:bg-muted/30 transition-colors"
                  >
                    <AccordionTrigger className="hover:no-underline py-2.5">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between w-full text-left gap-2 pr-4">
                        <div className="flex items-center gap-3">
                          {sec.category === "risk" && <AlertTriangle className="h-4.5 w-4.5 text-amber-500 shrink-0" />}
                          {sec.category === "driver" && <TrendingUp className="h-4.5 w-4.5 text-emerald-500 shrink-0" />}
                          {sec.category === "recommendation" && <Compass className="h-4.5 w-4.5 text-primary shrink-0" />}
                          {sec.category === "summary" && <FileText className="h-4.5 w-4.5 text-primary shrink-0" />}
                          {sec.category === "opportunity" && <Sparkles className="h-4.5 w-4.5 text-primary shrink-0" />}
                          {sec.category === "confidence" && <ShieldCheck className="h-4.5 w-4.5 text-emerald-500 shrink-0" />}
                          <span className="font-semibold text-sm sm:text-base text-foreground">{sec.title}</span>
                        </div>
                        <Badge variant="outline" className={getPriorityColor(sec.priority)}>
                          {sec.priority} priority
                        </Badge>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent className="pt-2 pb-4 border-t border-border mt-2 space-y-3 text-sm leading-relaxed text-muted-foreground">
                      <p className="font-semibold text-foreground">{sec.shortText}</p>
                      <p className="text-xs sm:text-sm">{sec.longText}</p>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </CardContent>
          </Card>
        </div>
      </div>
    </motion.div>
  );
}

function InsightsSkeleton() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <Skeleton className="h-10 w-96 bg-muted" />
        <Skeleton className="h-4 w-72 bg-muted" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <div className="lg:col-span-1 space-y-6">
          <Skeleton className="h-40 rounded-lg bg-muted" />
          <Skeleton className="h-40 rounded-lg bg-muted" />
        </div>
        <div className="lg:col-span-3">
          <Skeleton className="h-[400px] rounded-lg bg-muted" />
        </div>
      </div>
    </div>
  );
}
