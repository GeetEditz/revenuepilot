import type { Metadata } from "next";
import "./globals.css";
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";
import { ThemeProvider } from "@/components/theme-provider";
import { DashboardShell } from "@/components/dashboard-shell";
import { QueryProvider } from "@/providers/query-provider";
import { ToastProvider } from "@/hooks/use-toast";
 
const geist = Geist({
  subsets: ["latin"],
  variable: "--font-sans",
});
 
export const metadata: Metadata = {
  title: "RevenuePilot AI | Probabilistic Forecasting & Budget Optimization",
  description: "AI-Assisted Probabilistic Revenue Forecasting & Budget Optimization for Ecommerce Marketing",
};
 
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className={cn("font-sans", geist.variable)}>
      <body className="antialiased min-h-screen">
        <QueryProvider>
          <ThemeProvider
            attribute="class"
            defaultTheme="dark"
            enableSystem
            disableTransitionOnChange
          >
            <ToastProvider>
              <DashboardShell>{children}</DashboardShell>
            </ToastProvider>
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}

