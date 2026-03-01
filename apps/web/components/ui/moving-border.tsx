"use client";

import { cn } from "@/lib/utils";
import { motion } from "motion/react";
import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";

type MovingBorderProps<T extends ElementType = "button"> = {
  as?: T;
  children: ReactNode;
  duration?: number;
  borderRadius?: string;
  containerClassName?: string;
  borderClassName?: string;
  className?: string;
} & ComponentPropsWithoutRef<T>;

export function MovingBorder<T extends ElementType = "button">({
  as,
  children,
  duration = 2000,
  borderRadius = "1.75rem",
  containerClassName,
  borderClassName,
  className,
  ...rest
}: MovingBorderProps<T>) {
  const Component = as || "button";

  return (
    <Component
      className={cn(
        "relative inline-flex h-12 overflow-hidden p-[1px]",
        containerClassName,
      )}
      style={{ borderRadius }}
      {...rest}
    >
      <div
        className={cn(
          "absolute inset-0",
          borderClassName,
        )}
        style={{ borderRadius }}
      >
        <motion.div
          className="absolute h-[200%] w-[200%]"
          style={{
            background:
              "conic-gradient(from 0deg, transparent 0 340deg, #0b6bcb 360deg)",
            top: "-50%",
            left: "-50%",
          }}
          animate={{ rotate: 360 }}
          transition={{
            duration: duration / 1000,
            repeat: Number.POSITIVE_INFINITY,
            ease: "linear",
          }}
        />
      </div>
      <div
        className={cn(
          "relative flex h-full w-full items-center justify-center bg-white px-6 py-2 text-sm font-semibold backdrop-blur-xl",
          className,
        )}
        style={{ borderRadius: `calc(${borderRadius} - 1px)` }}
      >
        {children}
      </div>
    </Component>
  );
}
