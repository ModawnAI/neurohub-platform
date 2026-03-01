"use client";

import { motion } from "motion/react";

interface PipelineFlowProps {
  className?: string;
}

const stages = [
  { label: "DICOM", x: 30 },
  { label: "BIDS", x: 130 },
  { label: "Pre-QC", x: 230 },
  { label: "Analysis", x: 340 },
  { label: "Fusion", x: 450 },
  { label: "Report", x: 555 },
];

export function PipelineFlow({ className }: PipelineFlowProps) {
  return (
    <svg
      viewBox="0 0 640 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* Connection lines */}
      {stages.slice(0, -1).map((stage, i) => (
        <motion.line
          key={`line-${i}`}
          x1={stage.x + 40}
          y1={50}
          x2={stages[i + 1].x}
          y2={50}
          stroke="#cbd5e1"
          strokeWidth="2"
          strokeDasharray="6 4"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.4, delay: 0.3 + i * 0.4 }}
        />
      ))}

      {/* Flow pulses */}
      {stages.slice(0, -1).map((stage, i) => (
        <motion.circle
          key={`flow-${i}`}
          r="3"
          fill="#0b6bcb"
          initial={{ cx: stage.x + 40, cy: 50, opacity: 0 }}
          animate={{
            cx: [stage.x + 40, stages[i + 1].x],
            cy: [50, 50],
            opacity: [0, 1, 1, 0],
          }}
          transition={{
            duration: 1,
            delay: 2.5 + i * 0.5,
            repeat: Number.POSITIVE_INFINITY,
            repeatDelay: 2,
          }}
        />
      ))}

      {/* Stage nodes */}
      {stages.map((stage, i) => (
        <g key={`stage-${i}`}>
          {/* Node glow */}
          <motion.circle
            cx={stage.x + 20}
            cy={50}
            r="22"
            fill="#0b6bcb"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.1, 0] }}
            transition={{
              duration: 2,
              delay: 0.5 + i * 0.4,
              repeat: Number.POSITIVE_INFINITY,
              repeatDelay: 1.5,
            }}
          />
          {/* Node circle */}
          <motion.circle
            cx={stage.x + 20}
            cy={50}
            r="16"
            fill="white"
            stroke="#0b6bcb"
            strokeWidth="2"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{
              duration: 0.3,
              delay: 0.2 + i * 0.3,
              type: "spring",
            }}
          />
          {/* Step number */}
          <motion.text
            x={stage.x + 20}
            y={54}
            textAnchor="middle"
            fontSize="12"
            fontWeight="700"
            fill="#0b6bcb"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 + i * 0.3 }}
          >
            {i + 1}
          </motion.text>
          {/* Label */}
          <motion.text
            x={stage.x + 20}
            y={85}
            textAnchor="middle"
            fontSize="11"
            fontWeight="500"
            fill="#475569"
            initial={{ opacity: 0, y: 90 }}
            animate={{ opacity: 1, y: 85 }}
            transition={{ delay: 0.5 + i * 0.3 }}
          >
            {stage.label}
          </motion.text>
        </g>
      ))}
    </svg>
  );
}
