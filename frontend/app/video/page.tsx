"use client";

import React from "react";
import { motion } from "framer-motion";

export default function VideoWalkthroughPage() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-black p-4 md:p-8">
      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-5xl aspect-video rounded-2xl overflow-hidden border border-white/10 shadow-2xl bg-zinc-900"
      >
        <video
          src="/demo.mp4"
          poster="/vid-thumbnail.jpg"
          className="w-full h-full object-contain"
          controls
          playsInline
        />
      </motion.div>
    </div>
  );
}
