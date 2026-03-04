"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash } from "phosphor-react";
import { updateServiceDefinition, type ServiceRead } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

interface VolumeDiscount {
  min_cases: number;
  discount_percent: number;
}

interface PricingData {
  base_price: number;
  per_case_price: number;
  currency: string;
  volume_discounts: VolumeDiscount[];
}

interface Props {
  service: ServiceRead;
}

export function ServicePricing({ service }: Props) {
  const { locale } = useTranslation();
  const ko = locale === "ko";
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const raw = service.pricing as Partial<PricingData> | null | undefined;
  const existing: PricingData = {
    base_price: raw?.base_price ?? 0,
    per_case_price: raw?.per_case_price ?? 0,
    currency: raw?.currency ?? "KRW",
    volume_discounts: raw?.volume_discounts ?? [],
  };
  const [pricing, setPricing] = useState<PricingData>(existing);

  const saveMut = useMutation({
    mutationFn: () =>
      updateServiceDefinition(service.id, { pricing: pricing as unknown as Record<string, unknown> }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
      queryClient.invalidateQueries({ queryKey: ["service", service.id] });
      addToast("success", ko ? "가격 설정 저장 완료" : "Pricing saved");
    },
    onError: () => addToast("error", ko ? "저장 실패" : "Save failed"),
  });

  const isDirty = JSON.stringify(pricing) !== JSON.stringify(existing);

  const addDiscount = () => {
    setPricing({
      ...pricing,
      volume_discounts: [...pricing.volume_discounts, { min_cases: 10, discount_percent: 5 }],
    });
  };

  const removeDiscount = (idx: number) => {
    setPricing({
      ...pricing,
      volume_discounts: pricing.volume_discounts.filter((_, i) => i !== idx),
    });
  };

  const updateDiscount = (idx: number, patch: Partial<VolumeDiscount>) => {
    setPricing({
      ...pricing,
      volume_discounts: pricing.volume_discounts.map((d, i) => (i === idx ? { ...d, ...patch } : d)),
    });
  };

  const formatKRW = (v: number) => new Intl.NumberFormat("ko-KR").format(v);

  return (
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <h3 className="panel-title">{ko ? "가격 설정" : "Pricing"}</h3>
          <p className="muted-text" style={{ fontSize: 12, marginTop: 2 }}>
            {ko ? "서비스 이용 요금을 설정합니다" : "Set service pricing"}
          </p>
        </div>
        {isDirty && (
          <button className="btn btn-primary btn-sm" onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
            {saveMut.isPending ? <span className="spinner" /> : ko ? "저장" : "Save"}
          </button>
        )}
      </div>

      <div className="stack-md">
        <div className="form-grid" style={{ gridTemplateColumns: "1fr 1fr 120px" }}>
          <label className="field">
            {ko ? "기본 요금 (원)" : "Base Price (KRW)"}
            <input
              className="input"
              type="number"
              min={0}
              step={1000}
              value={pricing.base_price}
              onChange={(e) => setPricing({ ...pricing, base_price: Number(e.target.value) })}
            />
            <span className="muted-text" style={{ fontSize: 11 }}>{formatKRW(pricing.base_price)}원</span>
          </label>
          <label className="field">
            {ko ? "건당 요금 (원)" : "Per Case Price (KRW)"}
            <input
              className="input"
              type="number"
              min={0}
              step={1000}
              value={pricing.per_case_price}
              onChange={(e) => setPricing({ ...pricing, per_case_price: Number(e.target.value) })}
            />
            <span className="muted-text" style={{ fontSize: 11 }}>{formatKRW(pricing.per_case_price)}원/{ko ? "건" : "case"}</span>
          </label>
          <label className="field">
            {ko ? "통화" : "Currency"}
            <select className="input" value={pricing.currency} onChange={(e) => setPricing({ ...pricing, currency: e.target.value })}>
              <option value="KRW">KRW (원)</option>
              <option value="USD">USD ($)</option>
            </select>
          </label>
        </div>

        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <p className="detail-label">{ko ? "대량 할인" : "Volume Discounts"}</p>
            <button className="btn btn-secondary btn-sm" onClick={addDiscount} style={{ fontSize: 11 }}>
              <Plus size={12} /> {ko ? "할인 추가" : "Add Discount"}
            </button>
          </div>
          {pricing.volume_discounts.length === 0 ? (
            <p className="muted-text" style={{ fontSize: 12 }}>{ko ? "설정된 할인이 없습니다." : "No volume discounts."}</p>
          ) : (
            <div className="stack-sm">
              {pricing.volume_discounts.map((d, idx) => (
                <div key={idx} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input
                    className="input"
                    type="number"
                    min={1}
                    value={d.min_cases}
                    onChange={(e) => updateDiscount(idx, { min_cases: Number(e.target.value) })}
                    style={{ width: 100 }}
                  />
                  <span className="muted-text" style={{ fontSize: 12 }}>{ko ? "건 이상" : "+ cases"}</span>
                  <input
                    className="input"
                    type="number"
                    min={0}
                    max={100}
                    value={d.discount_percent}
                    onChange={(e) => updateDiscount(idx, { discount_percent: Number(e.target.value) })}
                    style={{ width: 80 }}
                  />
                  <span className="muted-text" style={{ fontSize: 12 }}>%</span>
                  <button className="btn btn-danger" style={{ padding: "2px 4px" }} onClick={() => removeDiscount(idx)}>
                    <Trash size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Preview */}
        <div style={{ padding: 12, background: "var(--surface-2)", borderRadius: "var(--radius-sm)" }}>
          <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>{ko ? "예시 계산" : "Example Calculation"}</p>
          <p className="muted-text" style={{ fontSize: 12 }}>
            1{ko ? "건" : " case"}: {formatKRW(pricing.base_price + pricing.per_case_price)}{ko ? "원" : ` ${pricing.currency}`} | 5{ko ? "건" : " cases"}: {formatKRW(pricing.base_price + pricing.per_case_price * 5)}{ko ? "원" : ` ${pricing.currency}`} | 10{ko ? "건" : " cases"}: {formatKRW(pricing.base_price + pricing.per_case_price * 10)}{ko ? "원" : ` ${pricing.currency}`}
          </p>
        </div>
      </div>
    </div>
  );
}
