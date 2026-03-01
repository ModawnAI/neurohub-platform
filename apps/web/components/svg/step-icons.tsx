"use client";

import { motion } from "motion/react";

/* ── Step 1: Upload ── */
export function UploadIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 80 80" fill="none" className={className} aria-hidden="true">
      {/* Outer ring */}
      <motion.circle
        cx="40"
        cy="40"
        r="36"
        stroke="#0b6bcb"
        strokeWidth="2"
        fill="none"
        strokeDasharray="4 6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.3, rotate: 360 }}
        transition={{
          opacity: { duration: 0.5 },
          rotate: { duration: 15, repeat: Number.POSITIVE_INFINITY, ease: "linear" },
        }}
        style={{ transformOrigin: "40px 40px" }}
      />
      {/* Cloud body */}
      <motion.path
        d="M28 48 C22 48 18 44 18 39 C18 34 22 30 27 30 C28 24 33 20 40 20 C47 20 52 24 53 30 C58 30 62 34 62 39 C62 44 58 48 52 48"
        stroke="#0b6bcb"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1 }}
      />
      {/* Upload arrow */}
      <motion.path
        d="M40 55 V38 M34 43 L40 37 L46 43"
        stroke="#0b6bcb"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: [5, 0, -2, 0] }}
        transition={{
          opacity: { delay: 1, duration: 0.3 },
          y: { delay: 1, duration: 2, repeat: Number.POSITIVE_INFINITY },
        }}
      />
      {/* Particle effects */}
      {[0, 1, 2].map((i) => (
        <motion.circle
          key={`p-${i}`}
          cx={36 + i * 4}
          r="1.5"
          fill="#3b82f6"
          initial={{ cy: 55, opacity: 0 }}
          animate={{ cy: [55, 30], opacity: [0, 0.8, 0] }}
          transition={{
            delay: 1.5 + i * 0.3,
            duration: 1,
            repeat: Number.POSITIVE_INFINITY,
            repeatDelay: 1.5,
          }}
        />
      ))}
    </svg>
  );
}

/* ── Step 2: AI Analysis ── */
export function AnalysisIcon({ className }: { className?: string }) {
  const neurons = [
    { x: 20, y: 40 },
    { x: 40, y: 20 },
    { x: 40, y: 60 },
    { x: 60, y: 30 },
    { x: 60, y: 50 },
  ];
  const links: [number, number][] = [
    [0, 1], [0, 2], [1, 3], [1, 4], [2, 3], [2, 4],
  ];

  return (
    <svg viewBox="0 0 80 80" fill="none" className={className} aria-hidden="true">
      {/* Neural connections */}
      {links.map(([a, b], i) => (
        <motion.line
          key={`l-${i}`}
          x1={neurons[a]!.x}
          y1={neurons[a]!.y}
          x2={neurons[b]!.x}
          y2={neurons[b]!.y}
          stroke="#3b82f6"
          strokeWidth="1.5"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.4 }}
          transition={{ delay: 0.3 + i * 0.1, duration: 0.5 }}
        />
      ))}

      {/* Pulse along links */}
      {links.slice(0, 3).map(([a, b], i) => (
        <motion.circle
          key={`pulse-${i}`}
          r="2"
          fill="#0b6bcb"
          initial={{ opacity: 0 }}
          animate={{
            cx: [neurons[a]!.x, neurons[b]!.x],
            cy: [neurons[a]!.y, neurons[b]!.y],
            opacity: [0, 1, 0],
          }}
          transition={{
            duration: 1,
            delay: 1.5 + i * 0.5,
            repeat: Number.POSITIVE_INFINITY,
            repeatDelay: 2,
          }}
        />
      ))}

      {/* Neurons */}
      {neurons.map((n, i) => (
        <g key={`n-${i}`}>
          <motion.circle
            cx={n.x}
            cy={n.y}
            r="8"
            fill="#0b6bcb"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: [0, 0.12, 0.08] }}
            transition={{ delay: 0.5 + i * 0.1, duration: 1.5, repeat: Number.POSITIVE_INFINITY, repeatDelay: 1.5 }}
            style={{ transformOrigin: `${n.x}px ${n.y}px` }}
          />
          <motion.circle
            cx={n.x}
            cy={n.y}
            r="4"
            fill="#0b6bcb"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.3 + i * 0.1, type: "spring" }}
          />
        </g>
      ))}

      {/* Processing arc */}
      <motion.circle
        cx="40"
        cy="40"
        r="32"
        stroke="#0b6bcb"
        strokeWidth="2"
        strokeDasharray="20 80"
        fill="none"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.4, rotate: 360 }}
        transition={{
          opacity: { delay: 1, duration: 0.5 },
          rotate: { duration: 4, repeat: Number.POSITIVE_INFINITY, ease: "linear" },
        }}
        style={{ transformOrigin: "40px 40px" }}
      />
    </svg>
  );
}

/* ── Step 3: Results ── */
export function ResultsIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 80 80" fill="none" className={className} aria-hidden="true">
      {/* Dashboard frame */}
      <motion.rect
        x="12"
        y="12"
        width="56"
        height="56"
        rx="8"
        stroke="#0b6bcb"
        strokeWidth="2"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.8 }}
      />

      {/* Dividers */}
      <motion.line x1="40" y1="12" x2="40" y2="44" stroke="#0b6bcb" strokeWidth="1" opacity="0.3"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.5 }}
      />
      <motion.line x1="12" y1="44" x2="68" y2="44" stroke="#0b6bcb" strokeWidth="1" opacity="0.3"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.6 }}
      />

      {/* Top-left: mini line chart */}
      <motion.path
        d="M18 36 L23 30 L28 33 L33 24 L36 28"
        stroke="#0b6bcb"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ delay: 0.8, duration: 0.6 }}
      />

      {/* Top-right: score */}
      <motion.text
        x="54"
        y="33"
        textAnchor="middle"
        fontSize="14"
        fontWeight="800"
        fill="#0b6bcb"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
      >
        92
      </motion.text>
      <motion.text
        x="54"
        y="40"
        textAnchor="middle"
        fontSize="6"
        fill="#64748b"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.1 }}
      >
        SCORE
      </motion.text>

      {/* Bottom: bars */}
      {[0, 1, 2, 3, 4].map((i) => {
        const h = 6 + Math.random() * 14;
        return (
          <motion.rect
            key={`bar-${i}`}
            x={18 + i * 9}
            y={62 - h}
            width="6"
            height={h}
            rx="1"
            fill={i === 2 ? "#0b6bcb" : "#93c5fd"}
            initial={{ height: 0, y: 62 }}
            animate={{ height: h, y: 62 - h }}
            transition={{ delay: 1.2 + i * 0.1, type: "spring" }}
          />
        );
      })}

      {/* Scanning highlight */}
      <motion.rect
        x="12"
        y="12"
        width="56"
        height="4"
        rx="2"
        fill="#0b6bcb"
        initial={{ opacity: 0 }}
        animate={{ opacity: [0, 0.15, 0], y: [12, 64, 12] }}
        transition={{ delay: 2, duration: 3, repeat: Number.POSITIVE_INFINITY, repeatDelay: 1 }}
      />
    </svg>
  );
}

/* ── Step 4: Report Download ── */
export function ReportDownloadIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 80 80" fill="none" className={className} aria-hidden="true">
      {/* Document */}
      <motion.path
        d="M22 12 H50 L58 20 V68 H22 V12 Z"
        stroke="#0b6bcb"
        strokeWidth="2"
        fill="none"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.8 }}
      />
      {/* Corner fold */}
      <motion.path
        d="M50 12 V20 H58"
        stroke="#0b6bcb"
        strokeWidth="2"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ delay: 0.5, duration: 0.3 }}
      />

      {/* Content lines */}
      {[30, 38, 46, 54].map((y, i) => (
        <motion.rect
          key={`line-${i}`}
          x="28"
          y={y}
          width={20 + (i % 2 === 0 ? 10 : 0)}
          height="3"
          rx="1.5"
          fill="#93c5fd"
          initial={{ opacity: 0, width: 0 }}
          animate={{ opacity: 1, width: 20 + (i % 2 === 0 ? 10 : 0) }}
          transition={{ delay: 0.8 + i * 0.1, duration: 0.3 }}
        />
      ))}

      {/* Download arrow */}
      <motion.g
        initial={{ opacity: 0 }}
        animate={{ opacity: 1, y: [0, 3, 0] }}
        transition={{
          opacity: { delay: 1.5 },
          y: { delay: 1.5, duration: 1.5, repeat: Number.POSITIVE_INFINITY },
        }}
      >
        <path
          d="M40 58 V70 M35 66 L40 71 L45 66"
          stroke="#0b6bcb"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </motion.g>

      {/* Sparkle */}
      <motion.circle
        cx="56"
        cy="56"
        r="2"
        fill="#0b6bcb"
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: [0, 1, 0], scale: [0, 1, 0] }}
        transition={{ delay: 2, duration: 1, repeat: Number.POSITIVE_INFINITY, repeatDelay: 2 }}
      />
    </svg>
  );
}
