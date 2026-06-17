"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";
import { cn } from "@/lib/utils";
import rpBlack from "@/app/RP_BLACK.png";
import rpWhite from "@/app/RP_WHITE.png";
import {
  LayoutDashboard,
  TrendingUp,
  Sliders,
  Sparkles,
  Activity,
  Search,
  Sun,
  Moon,
  ChevronLeft,
  ChevronRight,
  User,
  LogOut,
  Settings,
  Bell,
  CheckCircle,
  Database,
  SearchIcon,
  Menu,
  X,
  RefreshCw,
  Video,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useHealth, usePrefetchAll } from "@/lib/hooks/useQueries";

const menuItems = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Forecast Analysis", href: "/forecast", icon: TrendingUp },
  { label: "Budget Simulator", href: "/simulator", icon: Sliders },
  { label: "AI Insights", href: "/insights", icon: Sparkles },
  { label: "Video Walkthrough", href: "/video", icon: Video },
  { label: "System Health", href: "/health", icon: Activity },
];

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Use TanStack Query for health
  const { data: healthData, refetchHealth } = useHealth();
  const backendConnected = !!healthData;
  const modelLoaded = healthData?.model_loaded ?? false;

  // Prefetch all critical data in background
  usePrefetchAll();

  const triggerRefresh = useCallback(async () => {
    setIsRefreshing(true);
    console.log("[DIAGNOSTICS] Re-evaluating gateway status...");
    try {
      await refetchHealth();
      console.log(`[DIAGNOSTICS] Sync Completed | API Online: true`);
    } catch (err) {
      console.error("[DIAGNOSTICS] Gateway sync failed.", err);
    } finally {
      setTimeout(() => setIsRefreshing(false), 800);
    }
  }, [refetchHealth]);

  return (
    <TooltipProvider delayDuration={100}>
      <div className="min-h-screen flex bg-background text-foreground transition-colors duration-300">
        {/* Sidebar for Desktop */}
        <aside
          className={cn(
            "hidden md:flex flex-col border-r border-border bg-card transition-all duration-300 z-30 sticky top-0 h-screen",
            isCollapsed ? "w-20" : "w-64"
          )}
        >
          {/* Sidebar Header */}
          <div className="h-16 flex items-center justify-between px-4 border-b border-border">
            <Link href="/" className="flex items-center gap-3 overflow-hidden select-none w-full">
              <div className="h-9 w-9 rounded-lg flex items-center justify-center shadow-sm shrink-0 overflow-hidden relative">
                <Image
                  src={rpBlack}
                  alt="RevenuePilot AI Logo"
                  className="h-full w-full object-contain dark:hidden block"
                  priority
                />
                <Image
                  src={rpWhite}
                  alt="RevenuePilot AI Logo"
                  className="h-full w-full object-contain dark:block hidden"
                  priority
                />
              </div>
              {!isCollapsed && (
                <span className="font-semibold text-base tracking-tight whitespace-nowrap animate-fade-in">
                  RevenuePilot AI
                </span>
              )}
            </Link>
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Tooltip key={item.href}>
                  <TooltipTrigger asChild>
                    <Link
                      href={item.href}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group relative duration-200",
                        isActive
                          ? "bg-secondary text-secondary-foreground shadow-sm"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground"
                      )}
                    >
                      <Icon className={cn("h-4 w-4 shrink-0 transition-transform group-hover:scale-105", isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground")} />
                      {!isCollapsed && (
                        <span className="truncate">{item.label}</span>
                      )}
                      {isActive && (
                        <motion.div
                          layoutId="activeIndicator"
                          className="absolute left-0 w-1 h-5 bg-primary rounded-r-md"
                          transition={{ type: "spring", stiffness: 380, damping: 30 }}
                        />
                      )}
                    </Link>
                  </TooltipTrigger>
                  {isCollapsed && (
                    <TooltipContent side="right">
                      {item.label}
                    </TooltipContent>
                  )}
                </Tooltip>
              );
            })}
          </nav>

          {/* Sidebar Footer */}
          <div className="p-4 border-t border-border space-y-4">
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="w-full hidden md:flex items-center justify-center py-2 border border-border rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </button>
          </div>
        </aside>

        {/* Mobile Sidebar */}
        <AnimatePresence>
          {mobileOpen && (
            <>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.4 }}
                exit={{ opacity: 0 }}
                onClick={() => setMobileOpen(false)}
                className="fixed inset-0 bg-black z-40 md:hidden"
              />
              <motion.aside
                initial={{ x: "-100%" }}
                animate={{ x: 0 }}
                exit={{ x: "-100%" }}
                transition={{ type: "spring", damping: 25, stiffness: 200 }}
                className="fixed inset-y-0 left-0 w-64 bg-card border-r border-border z-50 p-4 flex flex-col md:hidden"
              >
                <div className="flex items-center justify-between pb-4 border-b border-border mb-6">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded flex items-center justify-center shrink-0 overflow-hidden relative">
                      <Image
                        src={rpBlack}
                        alt="RevenuePilot AI Logo"
                        className="h-full w-full object-contain dark:hidden block"
                        priority
                      />
                      <Image
                        src={rpWhite}
                        alt="RevenuePilot AI Logo"
                        className="h-full w-full object-contain dark:block hidden"
                        priority
                      />
                    </div>
                    <span className="font-semibold text-lg">RevenuePilot AI</span>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)}>
                    <X className="h-5 w-5" />
                  </Button>
                </div>
                <nav className="flex-1 space-y-1">
                  {menuItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = pathname === item.href;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={() => setMobileOpen(false)}
                        className={cn(
                          "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                          isActive
                            ? "bg-secondary text-secondary-foreground"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground"
                        )}
                      >
                        <Icon className="h-4 w-4" />
                        {item.label}
                      </Link>
                    );
                  })}
                </nav>
              </motion.aside>
            </>
          )}
        </AnimatePresence>

        {/* Content Wrapper */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Top Navbar */}
          <header className="h-16 border-b border-border bg-card flex items-center justify-between px-4 md:px-6 sticky top-0 z-20">
            {/* Left Header */}
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden"
                onClick={() => setMobileOpen(true)}
              >
                <Menu className="h-5 w-5" />
              </Button>
            </div>

            {/* Right Header Status / Toggles */}
            <div className="flex items-center gap-3 md:gap-4">
              {/* Sync Button */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={triggerRefresh}
                    className="hidden sm:inline-flex"
                  >
                    <RefreshCw className={cn("h-4 w-4 text-muted-foreground", isRefreshing && "animate-spin text-foreground")} />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Sync Model Status</TooltipContent>
              </Tooltip>

              {/* Backend Status Badge */}
              <Badge variant="outline" className={cn(
                "px-2 py-0.5 text-xs font-semibold gap-1.5 flex items-center select-none shadow-sm border-transparent",
                backendConnected 
                  ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" 
                  : "bg-red-500/10 text-red-600 dark:text-red-400"
              )}>
                <span className={cn("w-1.5 h-1.5 rounded-full", backendConnected ? "bg-emerald-500" : "bg-red-500")} />
                {backendConnected ? "Backend Connected" : "Backend Disconnected"}
              </Badge>

              {/* Model Status Indicator */}
              <div className="hidden lg:flex items-center gap-1.5 text-xs font-medium bg-muted border border-border px-2.5 py-1 rounded-md text-muted-foreground select-none">
                <Database className="h-3.5 w-3.5 text-primary" />
                <span>Model:</span>
                {modelLoaded ? (
                  <span className="text-foreground font-semibold">Model Ready</span>
                ) : (
                  <span className="text-amber-500 font-semibold">Fallback Ready</span>
                )}
              </div>

              {/* Theme Toggle */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                  >
                    <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                    <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Toggle Theme</TooltipContent>
              </Tooltip>

              {/* Profile Menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="relative rounded-full h-8 w-8 overflow-hidden border border-border hover:opacity-90">
                    <User className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel>
                    <div className="flex flex-col">
                      <span className="font-semibold text-sm">Ad Operations Executive</span>
                      <span className="text-xs text-muted-foreground">growth-team@store.com</span>
                    </div>
                  </DropdownMenuLabel>

                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="cursor-pointer text-destructive focus:text-destructive focus:bg-destructive/10">
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>Logout</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </header>

          {/* Main Area */}
          <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-8">
            {children}
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
