"use client";

import type { ReactNode } from "react";

interface MetricCardProps {
  icon: ReactNode;
  label: string;
  value: number | string;
  iconBg: string;
  iconColor: string;
}

export function MetricCard({ icon, label, value, iconBg, iconColor }: MetricCardProps) {
  return (
    <div className="metric-card">
      <div className="metric-icon" style={{ background: iconBg, color: iconColor }}>
        {icon}
      </div>
      <div>
        <p className="metric-label">{label}</p>
        <p className="metric-value">{value}</p>
      </div>
    </div>
  );
}
