"use client";

import React from "react";
import { motion } from "framer-motion";
import { HeroVideoDialog } from "@/components/ui/hero-video-dialog";
import { ArrowLeft, Play, Sparkles, Video, Film } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function VideoWalkthroughPage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-8 max-w-4xl mx-auto"
    >
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border pb-6">
        <div className="space-y-1.5">
          <Link href="/" className="inline-flex items-center gap-1.5 text-xs text-primary font-semibold hover:underline mb-2 transition-all">
            <ArrowLeft className="h-3 w-3" />
            Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Video className="h-7 w-7 text-primary" />
            Platform Video Walkthrough
          </h1>
          <p className="text-muted-foreground text-sm">
            Watch the video presentation of RevenuePilot AI's probabilistic forecasting and budget optimization capabilities
          </p>
        </div>
      </div>

      {/* Main Video Display Card */}
      <Card className="border border-border/80 bg-card/60 backdrop-blur-md overflow-hidden shadow-xl">
        <CardHeader className="pb-4">
          <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
            <Sparkles className="h-4 w-4" />
            <span>Interactive Video Showcase</span>
          </div>
          <CardTitle className="text-lg font-bold mt-1.5">RevenuePilot AI in Action</CardTitle>
          <CardDescription className="text-xs">
            Click the play button below to launch the fullscreen video walkthrough player.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-6 pt-0 relative">
          <div className="relative rounded-xl overflow-hidden border border-border bg-black/40">
            <HeroVideoDialog
              className="w-full"
              animationStyle="from-center"
              videoSrc="/demo.mp4"
              thumbnailSrc="/video_thumbnail.png"
              thumbnailAlt="RevenuePilot AI Video Walkthrough"
            />
          </div>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="border border-primary/20 bg-primary/5 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold flex items-center gap-2 text-primary">
            <Film className="h-4 w-4" />
            About This Walkthrough
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground leading-relaxed space-y-2">
          <p>
            This walkthrough demonstrates the core user experience of the **RevenuePilot AI** platform, detailing how ecommerce agencies analyze quantile regression curves and dynamically simulate multi-channel budgets across Google, Meta, and Microsoft Bing.
          </p>
          <p>
            Key highlights: LightGBM probabilistic forecasting bands, elastic sliding channel spend limits, backdrop-blurred fullscreen loading animations, and automated fallback strategic intelligence reports.
          </p>
        </CardContent>
      </Card>
    </motion.div>
  );
}
