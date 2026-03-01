"use client";

import { cn } from "@/lib/utils";
import { motion, stagger, useAnimate, useInView } from "motion/react";
import { useEffect } from "react";

interface TextGenerateEffectProps {
  words: string;
  className?: string;
  filter?: boolean;
  duration?: number;
}

export function TextGenerateEffect({
  words,
  className,
  filter = true,
  duration = 0.5,
}: TextGenerateEffectProps) {
  const [scope, animate] = useAnimate();
  const isInView = useInView(scope, { once: true });
  const wordsArray = words.split(" ");

  useEffect(() => {
    if (isInView) {
      animate(
        "span",
        { opacity: 1, filter: filter ? "blur(0px)" : "none" },
        { duration, delay: stagger(0.08) },
      );
    }
  }, [isInView, animate, filter, duration]);

  return (
    <div className={cn("font-bold", className)} ref={scope}>
      <div className="leading-snug tracking-tight">
        {wordsArray.map((word, idx) => (
          <motion.span
            key={`${word}-${idx}`}
            className="inline-block"
            style={{ opacity: 0, filter: filter ? "blur(10px)" : "none" }}
          >
            {word}
            {idx < wordsArray.length - 1 && "\u00A0"}
          </motion.span>
        ))}
      </div>
    </div>
  );
}
