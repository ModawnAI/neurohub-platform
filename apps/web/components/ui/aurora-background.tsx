"use client";

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface AuroraBackgroundProps {
  children: ReactNode;
  className?: string;
}

export function AuroraBackground({ children, className }: AuroraBackgroundProps) {
  return (
    <div
      className={cn(
        "relative flex flex-col items-center justify-center overflow-hidden",
        className,
      )}
    >
      <div className="absolute inset-0 overflow-hidden">
        <div
          className={cn(
            "pointer-events-none absolute -inset-[10px] opacity-50",
            "[--aurora:repeating-linear-gradient(100deg,#0b6bcb_10%,#3b82f6_15%,#6366f1_20%,#dbeafe_25%,#0b6bcb_30%)]",
            "[background-image:var(--aurora)]",
            "[background-size:300%_200%]",
            "[background-position:50%_50%]",
            "filter blur-[10px]",
            "after:content-[''] after:absolute after:inset-0",
            "after:[background-image:var(--aurora)]",
            "after:[background-size:200%_100%]",
            "after:[background-attachment:fixed]",
            "after:mix-blend-mode-difference",
            "animate-aurora",
          )}
          style={{
            backgroundImage:
              "repeating-linear-gradient(100deg, #0b6bcb 10%, #3b82f6 15%, #6366f1 20%, #dbeafe 25%, #0b6bcb 30%)",
            backgroundSize: "300% 200%",
            animation: "aurora 60s linear infinite",
            filter: "blur(10px)",
            opacity: 0.5,
          }}
        />
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              "repeating-linear-gradient(100deg, #0b6bcb 10%, #3b82f6 15%, #93c5fd 20%, #dbeafe 25%, #0b6bcb 30%)",
            backgroundSize: "200% 100%",
            animation: "aurora 50s linear infinite reverse",
            filter: "blur(30px)",
            opacity: 0.3,
          }}
        />
      </div>
      <div className="relative z-10 w-full">{children}</div>
    </div>
  );
}
