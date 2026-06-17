"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { X, CheckCircle2, AlertCircle, Info } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export type ToastType = "default" | "success" | "destructive" | "info";

export interface ToastProps {
  id: string;
  title?: string;
  description?: string;
  type?: ToastType;
  duration?: number;
}

interface ToastContextType {
  toast: (props: Omit<ToastProps, "id">) => void;
  toasts: ToastProps[];
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastProps[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    ({ title, description, type = "default", duration = 3000 }: Omit<ToastProps, "id">) => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev, { id, title, description, type, duration }]);

      if (duration > 0) {
        setTimeout(() => {
          dismiss(id);
        }, duration);
      }
    },
    [dismiss]
  );

  return (
    <ToastContext.Provider value={{ toast, toasts, dismiss }}>
      {children}
      <Toaster />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return {
    toast: context.toast,
    toasts: context.toasts,
    dismiss: context.dismiss,
  };
}

function Toaster() {
  const context = useContext(ToastContext);
  if (!context) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[10000] flex flex-col gap-2 w-full max-w-sm pointer-events-none">
      <AnimatePresence>
        {context.toasts.map((t) => {
          let bgClass = "bg-card border-border text-foreground";
          let Icon = Info;
          let iconColor = "text-muted-foreground";

          if (t.type === "success") {
            bgClass = "bg-emerald-950/90 border-emerald-800 text-emerald-100 backdrop-blur-md";
            Icon = CheckCircle2;
            iconColor = "text-emerald-400";
          } else if (t.type === "destructive") {
            bgClass = "bg-destructive/95 border-destructive text-destructive-foreground backdrop-blur-md";
            Icon = AlertCircle;
            iconColor = "text-white";
          } else if (t.type === "info") {
            bgClass = "bg-primary/95 border-primary/20 text-primary-foreground backdrop-blur-md";
            Icon = Info;
            iconColor = "text-white";
          }

          return (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.15 } }}
              layout
              className={`pointer-events-auto flex w-full items-start gap-3 rounded-lg border p-4 shadow-lg transition-all ${bgClass}`}
            >
              <Icon className={`h-5 w-5 shrink-0 mt-0.5 ${iconColor}`} />
              <div className="flex-1 space-y-1">
                {t.title && <h3 className="text-sm font-semibold tracking-tight">{t.title}</h3>}
                {t.description && <p className="text-xs opacity-90 leading-relaxed">{t.description}</p>}
              </div>
              <button
                onClick={() => context.dismiss(t.id)}
                className="shrink-0 rounded-md p-1 opacity-70 hover:opacity-100 hover:bg-black/10 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
