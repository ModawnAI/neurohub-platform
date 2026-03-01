"use client";

import { motion } from "motion/react";

interface QualityScanProps {
  className?: string;
}

export function QualityScan({ className }: QualityScanProps) {
  return (
    <svg
      viewBox="0 0 200 150"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* Document outline */}
      <motion.rect
        x="50"
        y="15"
        width="100"
        height="120"
        rx="8"
        stroke="#0b6bcb"
        strokeWidth="2"
        fill="white"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
      />

      {/* Data rows */}
      {[35, 55, 75, 95, 115].map((y, i) => (
        <motion.rect
          key={`row-${i}`}
          x="65"
          y={y}
          width={60 + (i % 2 === 0 ? 15 : 0)}
          height="6"
          rx="3"
          fill={i < 3 ? "#dbeafe" : "#e2e8f0"}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 + i * 0.1, duration: 0.3 }}
        />
      ))}

      {/* Scanning line sweeps down */}
      <motion.line
        x1="52"
        x2="148"
        stroke="#0b6bcb"
        strokeWidth="2"
        initial={{ y1: 17, y2: 17, opacity: 0 }}
        animate={{
          y1: [17, 133, 17],
          y2: [17, 133, 17],
          opacity: [0, 1, 1, 0.5, 0],
        }}
        transition={{
          duration: 2.5,
          delay: 1,
          repeat: Number.POSITIVE_INFINITY,
          repeatDelay: 1.5,
        }}
      />

      {/* Scan glow */}
      <motion.rect
        x="52"
        width="96"
        height="8"
        rx="1"
        fill="#0b6bcb"
        initial={{ y: 17, opacity: 0 }}
        animate={{
          y: [17, 133, 17],
          opacity: [0, 0.1, 0.1, 0.05, 0],
        }}
        transition={{
          duration: 2.5,
          delay: 1,
          repeat: Number.POSITIVE_INFINITY,
          repeatDelay: 1.5,
        }}
      />

      {/* Check marks appearing after scan */}
      {[35, 55, 75].map((y, i) => (
        <motion.path
          key={`check-${i}`}
          d={`M ${140} ${y + 3} l 3 3 6 -6`}
          stroke="#22c55e"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{
            delay: 3.5 + i * 0.3,
            duration: 0.3,
            repeat: Number.POSITIVE_INFINITY,
            repeatDelay: 3.7,
          }}
        />
      ))}

      {/* Warning for failed row */}
      <motion.g
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 4.4, duration: 0.3, repeat: Number.POSITIVE_INFINITY, repeatDelay: 3.7 }}
      >
        <circle cx="146" cy="98" r="5" fill="#fbbf24" />
        <text x="146" y="101" textAnchor="middle" fontSize="8" fontWeight="bold" fill="white">!</text>
      </motion.g>
    </svg>
  );
}
