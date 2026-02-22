"use client";

import { useCallback } from "react";
import { ko, type TranslationKeys } from "./ko";
import { en } from "./en";

const TRANSLATIONS: Record<string, TranslationKeys> = { ko, en };

type Locale = "ko" | "en";

let currentLocale: Locale = "ko";

export function setLocale(locale: Locale) {
  currentLocale = locale;
}

export function getLocale(): Locale {
  return currentLocale;
}

type NestedKeyOf<T> = T extends Record<string, unknown>
  ? {
      [K in keyof T & string]: T[K] extends Record<string, unknown>
        ? `${K}.${NestedKeyOf<T[K]>}`
        : K;
    }[keyof T & string]
  : never;

type TranslationKey = NestedKeyOf<TranslationKeys>;

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

export function t(key: TranslationKey): string {
  const translations = TRANSLATIONS[currentLocale] ?? ko;
  return getNestedValue(translations as unknown as Record<string, unknown>, key);
}

export function useT() {
  return useCallback((key: TranslationKey): string => {
    return t(key);
  }, []);
}
