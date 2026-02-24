"use client";

import { Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { XCircle } from "phosphor-react";
import { useTranslation } from "@/lib/i18n";

function PaymentFailContent() {
  const { t } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();

  const errorCode = searchParams.get("code") || "";
  const errorMessage = searchParams.get("message") || t("payment.genericError");

  return (
    <div className="stack-lg" style={{ maxWidth: 500, margin: "0 auto", textAlign: "center", paddingTop: 64 }}>
      <XCircle size={64} weight="fill" style={{ color: "var(--error)", margin: "0 auto" }} />
      <h1 className="page-title">{t("payment.failTitle")}</h1>
      <p className="page-subtitle">{errorMessage}</p>
      {errorCode && (
        <p style={{ fontSize: 13, color: "var(--muted)" }}>
          {t("payment.errorCode")}: {errorCode}
        </p>
      )}
      <button className="btn btn-primary" style={{ width: "100%", marginTop: 16 }} onClick={() => router.push("/user/payment")}>
        {t("payment.retry")}
      </button>
    </div>
  );
}

export default function PaymentFailPage() {
  return (
    <Suspense fallback={<div style={{ textAlign: "center", paddingTop: 64 }}><span className="spinner" /></div>}>
      <PaymentFailContent />
    </Suspense>
  );
}
