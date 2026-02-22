"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { ko, type TranslationKeys } from "./ko";
import { en } from "./en";
import React from "react";

const TRANSLATIONS: Record<string, TranslationKeys> = { ko, en };

export type Locale = "ko" | "en";

const STORAGE_KEY = "neurohub-locale";

function getInitialLocale(): Locale {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "ko" || stored === "en") return stored;
  }
  return "ko";
}

type NestedKeyOf<T> = T extends Record<string, unknown>
  ? {
      [K in keyof T & string]: T[K] extends Record<string, unknown>
        ? `${K}.${NestedKeyOf<T[K]>}`
        : K;
    }[keyof T & string]
  : never;

export type TranslationKey = NestedKeyOf<TranslationKeys>;

function getNestedValue(obj: Record<string, unknown>, path: string): string {
  const parts = path.split(".");
  let current: unknown = obj;
  for (const part of parts) {
    if (current && typeof current === "object" && part in current) {
      current = (current as Record<string, unknown>)[part];
    } else {
      return path;
    }
  }
  return typeof current === "string" ? current : path;
}

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

const LocaleContext = createContext<LocaleContextValue>({
  locale: "ko",
  setLocale: () => {},
});

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("ko");

  useEffect(() => {
    setLocaleState(getInitialLocale());
  }, []);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, next);
    }
  }, []);

  return React.createElement(
    LocaleContext.Provider,
    { value: { locale, setLocale } },
    children,
  );
}

export function useLocale() {
  return useContext(LocaleContext);
}

export function useT() {
  const { locale } = useContext(LocaleContext);
  return useCallback(
    (key: TranslationKey): string => {
      const translations = TRANSLATIONS[locale] ?? ko;
      return getNestedValue(translations as unknown as Record<string, unknown>, key);
    },
    [locale],
  );
}

/** Non-hook translation for use outside React components */
export function t(key: TranslationKey, locale: Locale = "ko"): string {
  const translations = TRANSLATIONS[locale] ?? ko;
  return getNestedValue(translations as unknown as Record<string, unknown>, key);
}
