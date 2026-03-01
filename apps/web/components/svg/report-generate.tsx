"use client";

import { motion } from "motion/react";

interface ReportGenerateProps {
  className?: string;
}

export function ReportGenerate({ className }: ReportGenerateProps) {
  return (
    <svg
      viewBox="0 0 200 150"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* Background page shadow */}
      <motion.rect
        x="63"
        y="18"
        width="80"
        height="110"
        rx="6"
        fill="#e2e8f0"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.5 }}
        transition={{ delay: 0.2 }}
      />

      {/* Main document */}
      <motion.rect
        x="58"
        y="13"
        width="80"
        height="110"
        rx="6"
        fill="white"
        stroke="#0b6bcb"
        strokeWidth="2"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      />

      {/* Header bar */}
      <motion.rect
        x="58"
        y="13"
        width="80"
        height="20"
        rx="6"
        fill="#0b6bcb"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      />
      <motion.text
        x="98"
        y="27"
        textAnchor="middle"
        fontSize="8"
        fontWeight="700"
        fill="white"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        REPORT
      </motion.text>

      {/* Chart area */}
      <motion.rect
        x="68"
        y="40"
        width="60"
        height="30"
        rx="4"
        fill="#eff6ff"
        stroke="#dbeafe"
        strokeWidth="1"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
      />

      {/* Mini bar chart */}
      {[0, 1, 2, 3, 4].map((i) => (
        <motion.rect
          key={`bar-${i}`}
          x={74 + i * 10}
          width="6"
          rx="1"
          fill="#0b6bcb"
          initial={{ height: 0, y: 65, opacity: 0 }}
          animate={{
            height: [0, 8 + Math.random() * 16],
            y: [65, 65 - (8 + Math.random() * 16)],
            opacity: 1,
          }}
          transition={{ delay: 0.8 + i * 0.1, duration: 0.4, type: "spring" }}
        />
      ))}

      {/* Text lines */}
      {[78, 88, 98, 108].map((y, i) => (
        <motion.rect
          key={`line-${i}`}
          x="68"
          y={y}
          width={40 + (i % 2 === 0 ? 18 : 8)}
          height="4"
          rx="2"
          fill={i < 2 ? "#cbd5e1" : "#e2e8f0"}
          initial={{ opacity: 0, width: 0 }}
          animate={{ opacity: 1, width: 40 + (i % 2 === 0 ? 18 : 8) }}
          transition={{ delay: 1.2 + i * 0.1, duration: 0.3 }}
        />
      ))}

      {/* Download arrow animation */}
      <motion.g
        initial={{ opacity: 0, y: -5 }}
        animate={{ opacity: [0, 1, 1, 0], y: [-5, 0, 5, 10] }}
        transition={{ delay: 2.5, duration: 1.2, repeat: Number.POSITIVE_INFINITY, repeatDelay: 2 }}
      >
        <path
          d="M155 70 v 15 l-5-5 M155 85 l5-5"
          stroke="#0b6bcb"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </motion.g>

      {/* PDF badge */}
      <motion.g
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 2, type: "spring" }}
      >
        <rect x="148" y="90" width="28" height="16" rx="4" fill="#dc2626" />
        <text x="162" y="101" textAnchor="middle" fontSize="7" fontWeight="800" fill="white">
          PDF
        </text>
      </motion.g>
    </svg>
  );
}
