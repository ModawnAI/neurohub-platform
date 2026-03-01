"use client";

import { motion } from "motion/react";

interface ShieldSecureProps {
  className?: string;
}

export function ShieldSecure({ className }: ShieldSecureProps) {
  return (
    <svg
      viewBox="0 0 200 150"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* Shield outline */}
      <motion.path
        d="M100 15 L145 35 V75 C145 105 125 125 100 138 C75 125 55 105 55 75 V35 L100 15 Z"
        stroke="#0b6bcb"
        strokeWidth="2.5"
        fill="none"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.2, ease: "easeInOut" }}
      />

      {/* Shield fill */}
      <motion.path
        d="M100 15 L145 35 V75 C145 105 125 125 100 138 C75 125 55 105 55 75 V35 L100 15 Z"
        fill="#0b6bcb"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.06 }}
        transition={{ delay: 1, duration: 0.5 }}
      />

      {/* Lock body */}
      <motion.rect
        x="87"
        y="65"
        width="26"
        height="22"
        rx="4"
        fill="#0b6bcb"
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 1.3, type: "spring" }}
      />

      {/* Lock shackle */}
      <motion.path
        d="M92 65 V55 C92 48 95 44 100 44 C105 44 108 48 108 55 V65"
        stroke="#0b6bcb"
        strokeWidth="3"
        strokeLinecap="round"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ delay: 1.5, duration: 0.5 }}
      />

      {/* Lock keyhole */}
      <motion.circle
        cx="100"
        cy="74"
        r="3"
        fill="white"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.6 }}
      />
      <motion.rect
        x="99"
        y="76"
        width="2"
        height="5"
        rx="1"
        fill="white"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.7 }}
      />

      {/* Scanning ring */}
      <motion.circle
        cx="100"
        cy="76"
        r="35"
        stroke="#0b6bcb"
        strokeWidth="1"
        strokeDasharray="4 8"
        fill="none"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.3, rotate: 360 }}
        transition={{
          opacity: { delay: 2, duration: 0.5 },
          rotate: { duration: 10, repeat: Number.POSITIVE_INFINITY, ease: "linear" },
        }}
        style={{ transformOrigin: "100px 76px" }}
      />

      {/* Pulse ring */}
      <motion.circle
        cx="100"
        cy="76"
        r="28"
        stroke="#0b6bcb"
        strokeWidth="1.5"
        fill="none"
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: [0.8, 1.3], opacity: [0.4, 0] }}
        transition={{
          delay: 2.5,
          duration: 1.5,
          repeat: Number.POSITIVE_INFINITY,
          repeatDelay: 1,
        }}
        style={{ transformOrigin: "100px 76px" }}
      />

      {/* Data bits orbiting */}
      {[0, 60, 120, 180, 240, 300].map((deg, i) => {
        const rad = (deg * Math.PI) / 180;
        const cx = 100 + 42 * Math.cos(rad);
        const cy = 76 + 42 * Math.sin(rad);
        return (
          <motion.circle
            key={`bit-${i}`}
            cx={cx}
            cy={cy}
            r="2"
            fill="#3b82f6"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.6, 0] }}
            transition={{
              delay: 2 + i * 0.3,
              duration: 1.5,
              repeat: Number.POSITIVE_INFINITY,
              repeatDelay: 1.5,
            }}
          />
        );
      })}
    </svg>
  );
}
