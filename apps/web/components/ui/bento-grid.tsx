"use client";

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface BentoGridProps {
  children: ReactNode;
  className?: string;
}

export function BentoGrid({ children, className }: BentoGridProps) {
  return (
    <div
      className={cn(
        "mx-auto grid max-w-7xl grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3",
        className,
      )}
    >
      {children}
    </div>
  );
}

interface BentoGridItemProps {
  title: string;
  description: string;
  icon?: ReactNode;
  header?: ReactNode;
  className?: string;
}

export function BentoGridItem({
  title,
  description,
  icon,
  header,
  className,
}: BentoGridItemProps) {
  return (
    <div
      className={cn(
        "group/bento row-span-1 flex flex-col justify-between space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-all duration-200 hover:shadow-md",
        className,
      )}
    >
      {header}
      <div className="transition duration-200">
        {icon}
        <h3 className="mb-2 mt-2 text-lg font-semibold text-slate-900">
          {title}
        </h3>
        <p className="text-sm leading-relaxed text-slate-500">
          {description}
        </p>
      </div>
    </div>
  );
}
