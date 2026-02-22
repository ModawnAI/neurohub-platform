"use client";

import { useLocale, useT } from "@/lib/i18n";
import { Globe } from "phosphor-react";

export function LanguageSwitcher() {
  const { locale, setLocale } = useLocale();
  const t = useT();

  const toggle = () => {
    setLocale(locale === "ko" ? "en" : "ko");
  };

  return (
    <button
      onClick={toggle}
      className="sidebar-action-btn"
      title={locale === "ko" ? t("sidebar.switchToEn") : t("sidebar.switchToKo")}
    >
      <Globe size={16} style={{ marginRight: 4 }} />
      {locale === "ko" ? "EN" : "KO"}
    </button>
  );
}
