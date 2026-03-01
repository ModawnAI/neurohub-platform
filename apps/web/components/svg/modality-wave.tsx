"use client";

import { motion } from "motion/react";

interface ModalityWaveProps {
  className?: string;
}

export function ModalityWave({ className }: ModalityWaveProps) {
  const modalities = [
    { label: "PET", y: 25, color: "#0b6bcb", delay: 0 },
    { label: "MRI", y: 50, color: "#3b82f6", delay: 0.3 },
    { label: "DTI", y: 75, color: "#6366f1", delay: 0.6 },
    { label: "fMRI", y: 100, color: "#818cf8", delay: 0.9 },
    { label: "EEG", y: 125, color: "#93c5fd", delay: 1.2 },
  ];

  return (
    <svg
      viewBox="0 0 400 150"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* Grid lines */}
      {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
        <line
          key={`grid-${i}`}
          x1={50 + i * 40}
          y1={10}
          x2={50 + i * 40}
          y2={140}
          stroke="#e2e8f0"
          strokeWidth="0.5"
          opacity="0.5"
        />
      ))}

      {/* Animated waveforms per modality */}
      {modalities.map((mod, idx) => (
        <g key={mod.label}>
          {/* Wave path */}
          <motion.path
            d={`M 50 ${mod.y} Q 90 ${mod.y - 12} 130 ${mod.y} T 210 ${mod.y} T 290 ${mod.y} T 370 ${mod.y}`}
            stroke={mod.color}
            strokeWidth="2"
            fill="none"
            strokeLinecap="round"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: 1.2, delay: mod.delay, ease: "easeOut" }}
          />

          {/* Traveling pulse */}
          <motion.circle
            r="3"
            fill={mod.color}
            initial={{ cx: 50, cy: mod.y, opacity: 0 }}
            animate={{
              cx: [50, 130, 210, 290, 370],
              cy: [mod.y, mod.y - 8, mod.y, mod.y - 8, mod.y],
              opacity: [0, 1, 1, 1, 0],
            }}
            transition={{
              duration: 3,
              delay: 2 + idx * 0.5,
              repeat: Number.POSITIVE_INFINITY,
              repeatDelay: 2,
            }}
          />

          {/* Glow at pulse */}
          <motion.circle
            r="8"
            fill={mod.color}
            initial={{ cx: 50, cy: mod.y, opacity: 0 }}
            animate={{
              cx: [50, 130, 210, 290, 370],
              cy: [mod.y, mod.y - 8, mod.y, mod.y - 8, mod.y],
              opacity: [0, 0.15, 0.15, 0.15, 0],
            }}
            transition={{
              duration: 3,
              delay: 2 + idx * 0.5,
              repeat: Number.POSITIVE_INFINITY,
              repeatDelay: 2,
            }}
          />

          {/* Label */}
          <motion.text
            x={18}
            y={mod.y + 4}
            fontSize="9"
            fontWeight="700"
            fill={mod.color}
            textAnchor="middle"
            initial={{ opacity: 0, x: 0 }}
            animate={{ opacity: 1, x: 18 }}
            transition={{ delay: mod.delay + 0.5, duration: 0.4 }}
          >
            {mod.label}
          </motion.text>
        </g>
      ))}

      {/* Convergence point */}
      <motion.circle
        cx="370"
        cy="75"
        r="5"
        fill="#0b6bcb"
        initial={{ scale: 0 }}
        animate={{ scale: [0, 1.2, 1] }}
        transition={{ delay: 2, duration: 0.6, type: "spring" }}
      />
      <motion.circle
        cx="370"
        cy="75"
        r="14"
        stroke="#0b6bcb"
        strokeWidth="1.5"
        fill="none"
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: [0, 1.5, 1], opacity: [0, 0.3, 0] }}
        transition={{ delay: 2.3, duration: 1.5, repeat: Number.POSITIVE_INFINITY, repeatDelay: 2 }}
      />
    </svg>
  );
}
