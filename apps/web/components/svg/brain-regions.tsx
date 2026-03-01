"use client";

import { motion } from "motion/react";
import { useState } from "react";

interface BrainRegionsProps {
  className?: string;
  activeRegion?: string | null;
}

const regions = [
  {
    id: "frontal",
    label: "Frontal Lobe",
    path: "M180 80 C 140 70, 100 90, 90 130 C 85 150, 95 170, 120 180 L 180 180 L 180 80 Z",
    color: "#3b82f6",
  },
  {
    id: "parietal",
    label: "Parietal Lobe",
    path: "M180 80 L 180 180 L 260 180 C 280 170, 300 140, 290 110 C 280 85, 240 70, 180 80 Z",
    color: "#6366f1",
  },
  {
    id: "temporal",
    label: "Temporal Lobe",
    path: "M90 130 C 80 160, 75 200, 90 230 C 100 250, 130 260, 160 260 L 180 260 L 180 180 L 120 180 C 100 175, 88 155, 90 130 Z",
    color: "#0b6bcb",
  },
  {
    id: "occipital",
    label: "Occipital Lobe",
    path: "M260 180 L 180 180 L 180 260 L 220 260 C 260 255, 290 230, 300 200 C 305 175, 290 170, 260 180 Z",
    color: "#2563eb",
  },
  {
    id: "cerebellum",
    label: "Cerebellum",
    path: "M160 260 C 140 270, 120 290, 130 310 C 140 330, 170 340, 200 340 C 230 340, 260 330, 270 310 C 280 290, 260 270, 240 260 L 160 260 Z",
    color: "#1d4ed8",
  },
  {
    id: "brainstem",
    label: "Brain Stem",
    path: "M190 300 C 185 320, 185 350, 190 370 L 210 370 C 215 350, 215 320, 210 300 L 190 300 Z",
    color: "#1e40af",
  },
];

export function BrainRegions({ className, activeRegion }: BrainRegionsProps) {
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null);

  return (
    <svg
      viewBox="0 0 400 400"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* Brain outline */}
      <motion.path
        d="M200 60 C 100 60, 60 120, 70 180 C 60 210, 55 240, 80 280 C 90 310, 130 350, 200 380 C 270 350, 310 310, 320 280 C 345 240, 340 210, 330 180 C 340 120, 300 60, 200 60 Z"
        stroke="#e2e8f0"
        strokeWidth="2"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.5 }}
      />

      {/* Regions */}
      {regions.map((region) => {
        const isActive = activeRegion === region.id || hoveredRegion === region.id;
        return (
          <motion.path
            key={region.id}
            d={region.path}
            fill={region.color}
            stroke={isActive ? region.color : "#e2e8f0"}
            strokeWidth={isActive ? 2 : 1}
            initial={{ opacity: 0 }}
            animate={{
              opacity: isActive ? 0.6 : 0.15,
              scale: isActive ? 1.02 : 1,
            }}
            transition={{ duration: 0.3 }}
            onMouseEnter={() => setHoveredRegion(region.id)}
            onMouseLeave={() => setHoveredRegion(null)}
            style={{ cursor: "pointer", transformOrigin: "center" }}
          />
        );
      })}
    </svg>
  );
}
