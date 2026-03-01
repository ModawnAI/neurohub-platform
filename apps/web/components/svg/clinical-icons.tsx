"use client";

import { motion } from "motion/react";

/* ── Epilepsy: Brain with focal zones ── */
export function EpilepsyIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 120" fill="none" className={className} aria-hidden="true">
      {/* Brain outline */}
      <motion.path
        d="M60 15 C35 15 18 35 20 58 C18 68 22 82 35 92 C45 100 55 106 60 108 C65 106 75 100 85 92 C98 82 102 68 100 58 C102 35 85 15 60 15 Z"
        stroke="#3b82f6"
        strokeWidth="2"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.2 }}
      />
      {/* Brain fill */}
      <motion.path
        d="M60 15 C35 15 18 35 20 58 C18 68 22 82 35 92 C45 100 55 106 60 108 C65 106 75 100 85 92 C98 82 102 68 100 58 C102 35 85 15 60 15 Z"
        fill="#3b82f6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.05 }}
        transition={{ delay: 1 }}
      />
      {/* Focal zone pulse */}
      <motion.circle
        cx="45"
        cy="55"
        r="10"
        fill="#ef4444"
        initial={{ opacity: 0 }}
        animate={{ opacity: [0, 0.3, 0] }}
        transition={{ delay: 1.5, duration: 1.5, repeat: Number.POSITIVE_INFINITY }}
      />
      <motion.circle
        cx="45"
        cy="55"
        r="5"
        fill="#ef4444"
        initial={{ opacity: 0 }}
        animate={{ opacity: [0, 0.6, 0.4] }}
        transition={{ delay: 1.5, duration: 1, repeat: Number.POSITIVE_INFINITY, repeatDelay: 0.5 }}
      />
      {/* EEG-style waves */}
      <motion.path
        d="M25 75 l5 -8 3 12 5 -15 4 10 4 -6 3 8 5 -10"
        stroke="#ef4444"
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 0.6 }}
        transition={{ delay: 2, duration: 0.8, repeat: Number.POSITIVE_INFINITY, repeatDelay: 2 }}
      />
      {/* Asymmetry indicators */}
      <motion.text x="35" y="45" fontSize="8" fontWeight="700" fill="#3b82f6"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.8 }}>L</motion.text>
      <motion.text x="78" y="45" fontSize="8" fontWeight="700" fill="#3b82f6"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.8 }}>R</motion.text>
    </svg>
  );
}

/* ── Dementia: Brain with atrophy zones ── */
export function DementiaIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 120" fill="none" className={className} aria-hidden="true">
      {/* Brain outline */}
      <motion.path
        d="M60 15 C35 15 18 35 20 58 C18 68 22 82 35 92 C45 100 55 106 60 108 C65 106 75 100 85 92 C98 82 102 68 100 58 C102 35 85 15 60 15 Z"
        stroke="#6366f1"
        strokeWidth="2"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.2 }}
      />
      {/* Cortical regions - progressive fading */}
      {[
        { cx: 42, cy: 45, r: 12, delay: 0 },
        { cx: 75, cy: 48, r: 10, delay: 0.3 },
        { cx: 55, cy: 70, r: 14, delay: 0.6 },
        { cx: 68, cy: 80, r: 8, delay: 0.9 },
      ].map((region, i) => (
        <motion.circle
          key={`region-${i}`}
          cx={region.cx}
          cy={region.cy}
          r={region.r}
          fill="#6366f1"
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0.15, 0.08] }}
          transition={{ delay: 1.5 + region.delay, duration: 2, repeat: Number.POSITIVE_INFINITY, repeatDelay: 1.5 }}
        />
      ))}
      {/* Shrinking animation (atrophy indicator) */}
      <motion.circle
        cx="60"
        cy="60"
        r="30"
        stroke="#6366f1"
        strokeWidth="1"
        strokeDasharray="3 6"
        fill="none"
        initial={{ scale: 1.2, opacity: 0 }}
        animate={{ scale: [1.2, 0.9], opacity: [0, 0.4, 0] }}
        transition={{ delay: 2, duration: 2.5, repeat: Number.POSITIVE_INFINITY, repeatDelay: 1 }}
        style={{ transformOrigin: "60px 60px" }}
      />
      {/* Amyloid markers */}
      {[
        { x: 50, y: 40 }, { x: 70, y: 50 }, { x: 45, y: 65 },
        { x: 65, y: 75 }, { x: 55, y: 55 },
      ].map((dot, i) => (
        <motion.circle
          key={`amyloid-${i}`}
          cx={dot.x}
          cy={dot.y}
          r="2"
          fill="#a855f7"
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0.8, 0.4] }}
          transition={{ delay: 2.5 + i * 0.2, duration: 1.5, repeat: Number.POSITIVE_INFINITY, repeatDelay: 2 }}
        />
      ))}
    </svg>
  );
}

/* ── Parkinson's: Dopamine pathway ── */
export function ParkinsonIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 120" fill="none" className={className} aria-hidden="true">
      {/* Brain outline */}
      <motion.path
        d="M60 15 C35 15 18 35 20 58 C18 68 22 82 35 92 C45 100 55 106 60 108 C65 106 75 100 85 92 C98 82 102 68 100 58 C102 35 85 15 60 15 Z"
        stroke="#0b6bcb"
        strokeWidth="2"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.2 }}
      />
      {/* Substantia nigra (midbrain) */}
      <motion.ellipse
        cx="60"
        cy="82"
        rx="12"
        ry="6"
        fill="#0b6bcb"
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 0.6, scale: 1 }}
        transition={{ delay: 1.3, type: "spring" }}
      />
      {/* Dopamine pathway (nigrostriatal) */}
      <motion.path
        d="M60 76 C55 60 48 50 50 40 M60 76 C65 60 72 50 70 40"
        stroke="#0b6bcb"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ delay: 1.5, duration: 0.8 }}
      />
      {/* Striatum */}
      <motion.ellipse
        cx="50"
        cy="38"
        rx="8"
        ry="5"
        stroke="#0b6bcb"
        strokeWidth="1.5"
        fill="none"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2 }}
      />
      <motion.ellipse
        cx="70"
        cy="38"
        rx="8"
        ry="5"
        stroke="#0b6bcb"
        strokeWidth="1.5"
        fill="none"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2.1 }}
      />
      {/* Dopamine particles traveling up */}
      {[0, 1, 2].map((i) => (
        <motion.circle
          key={`dopa-l-${i}`}
          r="2.5"
          fill="#22d3ee"
          initial={{ opacity: 0 }}
          animate={{
            cx: [60, 55, 48, 50],
            cy: [76, 60, 50, 40],
            opacity: [0, 1, 1, 0],
          }}
          transition={{
            duration: 1.5,
            delay: 2.5 + i * 0.6,
            repeat: Number.POSITIVE_INFINITY,
            repeatDelay: 1,
          }}
        />
      ))}
      {[0, 1, 2].map((i) => (
        <motion.circle
          key={`dopa-r-${i}`}
          r="2.5"
          fill="#22d3ee"
          initial={{ opacity: 0 }}
          animate={{
            cx: [60, 65, 72, 70],
            cy: [76, 60, 50, 40],
            opacity: [0, 1, 1, 0],
          }}
          transition={{
            duration: 1.5,
            delay: 2.8 + i * 0.6,
            repeat: Number.POSITIVE_INFINITY,
            repeatDelay: 1,
          }}
        />
      ))}
    </svg>
  );
}

/* ── Brain Tumor: Segmentation ── */
export function TumorIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 120" fill="none" className={className} aria-hidden="true">
      {/* Brain outline */}
      <motion.path
        d="M60 15 C35 15 18 35 20 58 C18 68 22 82 35 92 C45 100 55 106 60 108 C65 106 75 100 85 92 C98 82 102 68 100 58 C102 35 85 15 60 15 Z"
        stroke="#2563eb"
        strokeWidth="2"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.2 }}
      />
      {/* Tumor mass */}
      <motion.circle
        cx="70"
        cy="50"
        r="14"
        fill="#dc2626"
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 0.25, scale: 1 }}
        transition={{ delay: 1.5, type: "spring" }}
      />
      <motion.circle
        cx="70"
        cy="50"
        r="10"
        fill="#dc2626"
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 0.4, scale: 1 }}
        transition={{ delay: 1.7, type: "spring" }}
      />
      {/* Segmentation outline */}
      <motion.circle
        cx="70"
        cy="50"
        r="14"
        stroke="#dc2626"
        strokeWidth="2"
        strokeDasharray="3 3"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ delay: 2, duration: 0.8 }}
      />
      {/* Measurement lines */}
      <motion.line
        x1="56" y1="50" x2="84" y2="50"
        stroke="#f97316"
        strokeWidth="1"
        strokeDasharray="2 2"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 0.8 }}
        transition={{ delay: 2.5, duration: 0.4 }}
      />
      <motion.line
        x1="70" y1="36" x2="70" y2="64"
        stroke="#f97316"
        strokeWidth="1"
        strokeDasharray="2 2"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 0.8 }}
        transition={{ delay: 2.7, duration: 0.4 }}
      />
      {/* Volume label */}
      <motion.g
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 3 }}
      >
        <rect x="78" y="68" width="28" height="14" rx="3" fill="#2563eb" />
        <text x="92" y="78" textAnchor="middle" fontSize="7" fontWeight="700" fill="white">12.3ml</text>
      </motion.g>
      {/* Scanning sweep */}
      <motion.line
        x1="20" y1="15" x2="20" y2="108"
        stroke="#2563eb"
        strokeWidth="1"
        initial={{ opacity: 0 }}
        animate={{ opacity: [0, 0.3, 0], x1: [20, 100], x2: [20, 100] }}
        transition={{ delay: 3.5, duration: 2, repeat: Number.POSITIVE_INFINITY, repeatDelay: 2 }}
      />
    </svg>
  );
}
