"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface UseWizardOptions<T> {
  totalSteps: number;
  draftKey?: string;
  initialDraft: T;
  /** Return true if the user can advance from the given step. */
  canAdvance?: (step: number, draft: T) => boolean;
}

interface UseWizardReturn<T> {
  step: number;
  draft: T;
  setDraft: (partial: Partial<T>) => void;
  replaceDraft: (full: T) => void;
  next: () => void;
  prev: () => void;
  goTo: (step: number) => void;
  canGoNext: boolean;
  isFirst: boolean;
  isLast: boolean;
  clearDraft: () => void;
  hasSavedDraft: boolean;
}

const DEBOUNCE_MS = 300;

export function useWizard<T extends Record<string, unknown>>(
  options: UseWizardOptions<T>,
): UseWizardReturn<T> {
  const { totalSteps, draftKey, initialDraft, canAdvance } = options;
  const [step, setStep] = useState(1);
  const [draft, setDraftState] = useState<T>(initialDraft);
  const [hasSavedDraft, setHasSavedDraft] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Restore draft from localStorage on mount
  useEffect(() => {
    if (!draftKey) return;
    try {
      const saved = localStorage.getItem(draftKey);
      if (saved) {
        const parsed = JSON.parse(saved) as { draft: T; step: number };
        setDraftState(parsed.draft);
        setStep(parsed.step);
        setHasSavedDraft(true);
      }
    } catch {
      // ignore parse errors
    }
  }, [draftKey]);

  // Auto-save draft to localStorage (debounced)
  useEffect(() => {
    if (!draftKey) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      try {
        localStorage.setItem(draftKey, JSON.stringify({ draft, step }));
      } catch {
        // storage full, ignore
      }
    }, DEBOUNCE_MS);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [draft, step, draftKey]);

  const setDraft = useCallback((partial: Partial<T>) => {
    setDraftState((prev) => ({ ...prev, ...partial }));
  }, []);

  const replaceDraft = useCallback((full: T) => {
    setDraftState(full);
  }, []);

  const canGoNext = canAdvance ? canAdvance(step, draft) : true;

  const next = useCallback(() => {
    if (step < totalSteps && canGoNext) setStep((s) => s + 1);
  }, [step, totalSteps, canGoNext]);

  const prev = useCallback(() => {
    if (step > 1) setStep((s) => s - 1);
  }, [step]);

  const goTo = useCallback(
    (target: number) => {
      if (target >= 1 && target <= totalSteps) setStep(target);
    },
    [totalSteps],
  );

  const clearDraft = useCallback(() => {
    setDraftState(initialDraft);
    setStep(1);
    setHasSavedDraft(false);
    if (draftKey) {
      try {
        localStorage.removeItem(draftKey);
      } catch {
        // ignore
      }
    }
  }, [initialDraft, draftKey]);

  return {
    step,
    draft,
    setDraft,
    replaceDraft,
    next,
    prev,
    goTo,
    canGoNext,
    isFirst: step === 1,
    isLast: step === totalSteps,
    clearDraft,
    hasSavedDraft,
  };
}
