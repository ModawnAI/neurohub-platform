"use client";

import { useT } from "@/lib/i18n";

export function SkipNav() {
  const t = useT();
  return (
    <a href="#main-content" className="skip-nav">
      {t("app.skipToMain")}
    </a>
  );
}
