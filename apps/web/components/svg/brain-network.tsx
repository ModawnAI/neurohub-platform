"use client";

import { motion } from "motion/react";

interface BrainNetworkProps {
  className?: string;
}

export function BrainNetwork({ className }: BrainNetworkProps) {
  const nodes = [
    { cx: 200, cy: 80, r: 6 },
    { cx: 260, cy: 110, r: 5 },
    { cx: 160, cy: 130, r: 7 },
    { cx: 300, cy: 160, r: 5 },
    { cx: 130, cy: 180, r: 6 },
    { cx: 240, cy: 190, r: 8 },
    { cx: 180, cy: 220, r: 5 },
    { cx: 280, cy: 230, r: 6 },
    { cx: 150, cy: 270, r: 5 },
    { cx: 220, cy: 280, r: 7 },
    { cx: 300, cy: 270, r: 5 },
    { cx: 200, cy: 340, r: 6 },
  ];

  const connections = [
    [0, 1], [0, 2], [1, 3], [1, 5], [2, 4], [2, 6],
    [3, 5], [3, 7], [4, 6], [5, 6], [5, 7], [5, 9],
    [6, 8], [6, 9], [7, 10], [8, 9], [8, 11], [9, 10],
    [9, 11], [10, 11],
  ];

  return (
    <svg
      viewBox="0 0 400 420"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* Brain outline */}
      <motion.path
        d="M200 40 C 100 40, 60 100, 70 160 C 60 180, 55 220, 80 260 C 90 300, 120 340, 160 360 C 180 370, 200 380, 200 380 C 200 380, 220 370, 240 360 C 280 340, 310 300, 320 260 C 345 220, 340 180, 330 160 C 340 100, 300 40, 200 40 Z"
        stroke="#0b6bcb"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 2, ease: "easeInOut" }}
      />

      {/* Center line (cerebral fissure) */}
      <motion.path
        d="M200 50 C 200 50, 195 120, 200 180 C 205 240, 195 300, 200 375"
        stroke="#0b6bcb"
        strokeWidth="1"
        strokeDasharray="4 4"
        opacity="0.4"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.5, delay: 0.5 }}
      />

      {/* Neural connections */}
      {connections.map(([from, to], i) => (
        <motion.line
          key={`conn-${i}`}
          x1={nodes[from].cx}
          y1={nodes[from].cy}
          x2={nodes[to].cx}
          y2={nodes[to].cy}
          stroke="#3b82f6"
          strokeWidth="1.5"
          opacity="0.3"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.8, delay: 1 + i * 0.05 }}
        />
      ))}

      {/* Data flow pulses along connections */}
      {connections.slice(0, 8).map(([from, to], i) => (
        <motion.circle
          key={`pulse-${i}`}
          r="2"
          fill="#0b6bcb"
          initial={{
            cx: nodes[from].cx,
            cy: nodes[from].cy,
            opacity: 0,
          }}
          animate={{
            cx: [nodes[from].cx, nodes[to].cx],
            cy: [nodes[from].cy, nodes[to].cy],
            opacity: [0, 1, 1, 0],
          }}
          transition={{
            duration: 2,
            delay: 2 + i * 0.4,
            repeat: Number.POSITIVE_INFINITY,
            repeatDelay: 3,
          }}
        />
      ))}

      {/* Neural nodes */}
      {nodes.map((node, i) => (
        <g key={`node-${i}`}>
          {/* Glow */}
          <motion.circle
            cx={node.cx}
            cy={node.cy}
            r={node.r * 2.5}
            fill="#0b6bcb"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.15, 0] }}
            transition={{
              duration: 2,
              delay: 1.5 + i * 0.15,
              repeat: Number.POSITIVE_INFINITY,
              repeatDelay: 1,
            }}
          />
          {/* Core */}
          <motion.circle
            cx={node.cx}
            cy={node.cy}
            r={node.r}
            fill="#0b6bcb"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{
              duration: 0.4,
              delay: 1.5 + i * 0.1,
              type: "spring",
            }}
          />
        </g>
      ))}
    </svg>
  );
}
