"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { CreditCard } from "phosphor-react";
import { listServices, preparePayment, getPaymentHistory, type ServiceRead, type PaymentRead } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

export default function PaymentPage() {
  const { t, locale } = useTranslation();
  const dateLocale = locale === "ko" ? "ko-KR" : "en-US";
  const [selectedService, setSelectedService] = useState<ServiceRead | null>(null);
  const [tossReady, setTossReady] = useState(false);
  const widgetsRef = useRef<any>(null);
  const paymentWidgetRef = useRef<HTMLDivElement>(null);

  const { data: servicesData } = useQuery({
    queryKey: ["services"],
    queryFn: listServices,
  });
  const services = (servicesData?.items ?? []).filter(
    (s) => s.status === "ACTIVE" || s.status === "PUBLISHED"
  );
  const paidServices = services.filter((s) => s.pricing && s.pricing.base_price > 0);

  const { data: historyData } = useQuery({
    queryKey: ["payment-history"],
    queryFn: getPaymentHistory,
  });
  const payments = historyData?.items ?? [];

  const prepareMut = useMutation({
    mutationFn: () => {
      if (!selectedService || !selectedService.pricing) throw new Error("No service selected");
      return preparePayment({
        service_id: selectedService.id,
        amount: selectedService.pricing.base_price,
      });
    },
    onSuccess: async (data) => {
      const clientKey = process.env.NEXT_PUBLIC_TOSS_CLIENT_KEY;
      if (!clientKey) {
        alert("Toss client key not configured");
        return;
      }

      // Load Toss SDK dynamically
      if (!(window as any).TossPayments) {
        const script = document.createElement("script");
        script.src = "https://js.tosspayments.com/v2/standard";
        script.onload = () => initTossWidgets(data, clientKey);
        document.head.appendChild(script);
      } else {
        await initTossWidgets(data, clientKey);
      }
    },
  });

  async function initTossWidgets(
    data: { order_id: string; customer_key: string; amount: number },
    clientKey: string,
  ) {
    try {
      const tossPayments = (window as any).TossPayments(clientKey);
      const widgets = tossPayments.widgets({ customerKey: data.customer_key });
      await widgets.setAmount({ currency: "KRW", value: data.amount });

      if (paymentWidgetRef.current) {
        paymentWidgetRef.current.innerHTML = "";
        await widgets.renderPaymentMethods({
          selector: "#payment-widget",
          variantKey: "DEFAULT",
        });
      }

      widgetsRef.current = { widgets, orderId: data.order_id };
      setTossReady(true);
    } catch (err) {
      console.error("Toss init error:", err);
    }
  }

  async function handleConfirm() {
    if (!widgetsRef.current || !selectedService) return;
    const { widgets, orderId } = widgetsRef.current;
    try {
      await widgets.requestPayment({
        orderId,
        orderName: selectedService.display_name,
        successUrl: `${window.location.origin}/user/payment/success`,
        failUrl: `${window.location.origin}/user/payment/fail`,
      });
    } catch (err) {
      console.error("Payment request error:", err);
    }
  }

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("payment.title")}</h1>
          <p className="page-subtitle">{t("payment.subtitle")}</p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        {/* Left: Service Selection + Payment */}
        <div className="stack-md">
          <div className="panel">
            <div className="panel-header">{t("payment.selectService")}</div>
            <div className="stack-sm" style={{ padding: 16 }}>
              {paidServices.length === 0 ? (
                <p style={{ color: "var(--muted)" }}>No paid services available</p>
              ) : (
                paidServices.map((svc) => (
                  <button
                    key={svc.id}
                    className="panel"
                    style={{
                      cursor: "pointer",
                      textAlign: "left",
                      width: "100%",
                      border: selectedService?.id === svc.id ? "2px solid var(--primary)" : "1px solid var(--border)",
                      padding: 16,
                    }}
                    onClick={() => { setSelectedService(svc); setTossReady(false); }}
                  >
                    <div style={{ fontWeight: 600 }}>{svc.display_name}</div>
                    <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 4 }}>
                      {svc.service_type === "HUMAN_IN_LOOP" ? t("payment.humanInLoop") : t("payment.automatic")}
                      {svc.description && ` · ${svc.description}`}
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, marginTop: 8, color: "var(--primary)" }}>
                      ₩{svc.pricing?.base_price?.toLocaleString() ?? 0}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {selectedService && (
            <div className="panel" style={{ padding: 16 }}>
              {!tossReady && (
                <button
                  className="btn btn-primary"
                  style={{ width: "100%" }}
                  onClick={() => prepareMut.mutate()}
                  disabled={prepareMut.isPending}
                >
                  <CreditCard size={16} />
                  {prepareMut.isPending ? t("payment.preparing") : `${t("payment.payNow")} — ₩${selectedService.pricing?.base_price?.toLocaleString()}`}
                </button>
              )}
              <div id="payment-widget" ref={paymentWidgetRef} style={{ marginTop: 16 }} />
              {tossReady && (
                <button
                  className="btn btn-primary"
                  style={{ width: "100%", marginTop: 12 }}
                  onClick={handleConfirm}
                >
                  {t("payment.confirmPayment")}
                </button>
              )}
              {prepareMut.isError && (
                <p className="error-text" style={{ marginTop: 8 }}>{(prepareMut.error as Error).message}</p>
              )}
            </div>
          )}
        </div>

        {/* Right: Payment History */}
        <div className="panel">
          <div className="panel-header">{t("payment.history")}</div>
          {payments.length === 0 ? (
            <p style={{ padding: 16, color: "var(--muted)" }}>{t("payment.noHistory")}</p>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t("payment.orderId")}</th>
                    <th>{t("payment.method")}</th>
                    <th>{t("payment.amount")}</th>
                    <th>{t("common.status")}</th>
                    <th>{t("common.date")}</th>
                  </tr>
                </thead>
                <tbody>
                  {payments.map((p: PaymentRead) => (
                    <tr key={p.id}>
                      <td className="mono-cell">{p.order_id.slice(0, 12)}</td>
                      <td>{p.method || "-"}</td>
                      <td>₩{p.amount.toLocaleString()}</td>
                      <td>
                        <span className={`status-chip ${p.status === "CONFIRMED" ? "status-final" : p.status === "FAILED" ? "status-cancelled" : "status-pending"}`}>
                          {p.status}
                        </span>
                      </td>
                      <td>{new Date(p.created_at).toLocaleDateString(dateLocale)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
