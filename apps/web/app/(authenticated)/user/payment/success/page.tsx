"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle, ArrowRight } from "phosphor-react";
import { confirmPayment } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

function PaymentSuccessContent() {
  const { t } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [confirmed, setConfirmed] = useState(false);

  const paymentKey = searchParams.get("paymentKey") || "";
  const orderId = searchParams.get("orderId") || "";
  const amount = Number(searchParams.get("amount") || "0");

  const confirmMut = useMutation({
    mutationFn: () => confirmPayment({ payment_key: paymentKey, order_id: orderId, amount }),
    onSuccess: () => setConfirmed(true),
  });

  useEffect(() => {
    if (paymentKey && orderId && amount > 0) {
      confirmMut.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="stack-lg" style={{ maxWidth: 500, margin: "0 auto", textAlign: "center", paddingTop: 64 }}>
      {confirmMut.isPending && (
        <>
          <span className="spinner" />
          <p>{t("payment.confirming")}</p>
        </>
      )}

      {confirmed && (
        <>
          <CheckCircle size={64} weight="fill" style={{ color: "var(--success)", margin: "0 auto" }} />
          <h1 className="page-title">{t("payment.successTitle")}</h1>
          <p className="page-subtitle">{t("payment.successMessage")}</p>
          <div className="panel" style={{ padding: 16, textAlign: "left" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ color: "var(--muted)" }}>{t("payment.orderId")}</span>
              <span className="mono-cell">{orderId.slice(0, 16)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--muted)" }}>{t("payment.amount")}</span>
              <span style={{ fontWeight: 700 }}>{"\u20A9"}{amount.toLocaleString()}</span>
            </div>
          </div>
          <button className="btn btn-primary" style={{ width: "100%", marginTop: 16 }} onClick={() => router.push("/user/new-request")}>
            <ArrowRight size={16} /> {t("payment.goToNewRequest")}
          </button>
        </>
      )}

      {confirmMut.isError && (
        <>
          <h1 className="page-title">{t("payment.errorTitle")}</h1>
          <p className="error-text">{(confirmMut.error as Error).message}</p>
          <button className="btn btn-secondary" style={{ marginTop: 16 }} onClick={() => router.push("/user/payment")}>
            {t("payment.retry")}
          </button>
        </>
      )}
    </div>
  );
}

export default function PaymentSuccessPage() {
  return (
    <Suspense fallback={<div style={{ textAlign: "center", paddingTop: 64 }}><span className="spinner" /></div>}>
      <PaymentSuccessContent />
    </Suspense>
  );
}
