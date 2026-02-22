"use client";

import { getLocale, setLocale } from "@/lib/i18n";
import { Globe } from "phosphor-react";
import { useState } from "react";

export function LanguageSwitcher() {
  const [locale, setLocaleState] = useState(getLocale());

  const toggle = () => {
    const next = locale === "ko" ? "en" : "ko";
    setLocale(next as "ko" | "en");
    setLocaleState(next);
  };

  return (
    <button
      onClick={toggle}
      className="sidebar-link"
      style={{ width: "auto", padding: "6px 10px", display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}
      title={locale === "ko" ? "Switch to English" : "한국어로 전환"}
    >
      <Globe size={16} />
      {locale === "ko" ? "EN" : "KO"}
    </button>
  );
}
