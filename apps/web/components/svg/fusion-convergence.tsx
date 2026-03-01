"use client";

import { motion } from "motion/react";

interface FusionConvergenceProps {
  className?: string;
}

export function FusionConvergence({ className }: FusionConvergenceProps) {
  const streams = [
    { startX: 30, startY: 20, color: "#3b82f6" },
    { startX: 30, startY: 55, color: "#6366f1" },
    { startX: 30, startY: 90, color: "#0b6bcb" },
    { startX: 30, startY: 125, color: "#818cf8" },
  ];

  const centerX = 120;
  const centerY = 72;

  return (
    <svg
      viewBox="0 0 200 150"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* Converging streams */}
      {streams.map((s, i) => (
        <g key={`stream-${i}`}>
          {/* Stream line */}
          <motion.path
            d={`M ${s.startX} ${s.startY} C ${70} ${s.startY}, ${90} ${centerY}, ${centerX} ${centerY}`}
            stroke={s.color}
            strokeWidth="2"
            fill="none"
            strokeLinecap="round"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 0.6 }}
            transition={{ duration: 1, delay: i * 0.2 }}
          />

          {/* Data particles flowing in */}
          <motion.circle
            r="3"
            fill={s.color}
            initial={{ opacity: 0 }}
            animate={{
              cx: [s.startX, 70, 90, centerX],
              cy: [s.startY, s.startY, centerY, centerY],
              opacity: [0, 1, 1, 0],
            }}
            transition={{
              duration: 1.5,
              delay: 2 + i * 0.4,
              repeat: Number.POSITIVE_INFINITY,
              repeatDelay: 2.5,
            }}
          />

          {/* Source node */}
          <motion.circle
            cx={s.startX}
            cy={s.startY}
            r="4"
            fill={s.color}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2 + i * 0.15, type: "spring" }}
          />
        </g>
      ))}

      {/* Center fusion node */}
      <motion.circle
        cx={centerX}
        cy={centerY}
        r="18"
        fill="#0b6bcb"
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: [0, 1.1, 1], opacity: [0, 0.12, 0.08] }}
        transition={{ delay: 1.2, duration: 0.8, repeat: Number.POSITIVE_INFINITY, repeatDelay: 2 }}
      />
      <motion.circle
        cx={centerX}
        cy={centerY}
        r="10"
        fill="#0b6bcb"
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 1, type: "spring" }}
      />
      <motion.text
        x={centerX}
        y={centerY + 3.5}
        textAnchor="middle"
        fontSize="8"
        fontWeight="800"
        fill="white"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5 }}
      >
        Σ
      </motion.text>

      {/* Output ray */}
      <motion.line
        x1={centerX + 12}
        y1={centerY}
        x2={185}
        y2={centerY}
        stroke="#0b6bcb"
        strokeWidth="2"
        strokeLinecap="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ delay: 1.8, duration: 0.6 }}
      />

      {/* Output score */}
      <motion.g
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 2.4, type: "spring" }}
      >
        <rect x="165" y={centerY - 14} width="30" height="28" rx="6" fill="#0b6bcb" />
        <text x="180" y={centerY + 4} textAnchor="middle" fontSize="11" fontWeight="800" fill="white">
          92
        </text>
      </motion.g>

      {/* Orbiting ring */}
      <motion.circle
        cx={centerX}
        cy={centerY}
        r="25"
        stroke="#0b6bcb"
        strokeWidth="1"
        strokeDasharray="3 6"
        fill="none"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.3, rotate: 360 }}
        transition={{
          opacity: { delay: 1.5, duration: 0.5 },
          rotate: { duration: 8, repeat: Number.POSITIVE_INFINITY, ease: "linear" },
        }}
        style={{ transformOrigin: `${centerX}px ${centerY}px` }}
      />
    </svg>
  );
}
