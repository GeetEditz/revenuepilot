"use client";

import React from "react";
import { motion } from "framer-motion";
import { HeroVideoDialog } from "@/components/ui/hero-video-dialog";

export default function VideoWalkthroughPage() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-black p-4 md:p-8">
      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-5xl rounded-2xl overflow-hidden shadow-2xl"
      >
        <HeroVideoDialog
          className="w-full"
          animationStyle="from-center"
          videoSrc="/demo.mp4"
          thumbnailSrc="/vid-thumbnail.jpg"
          thumbnailAlt="RevenuePilot AI Video Walkthrough"
        />
      </motion.div>
    </div>
  );
}
