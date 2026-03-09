"use client";

import { listServices, type ServiceRead } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { MagnifyingGlass, Cube, ArrowRight, Brain, Lightning, Heartbeat } from "phosphor-react";
import { SkeletonCards } from "@/components/skeleton";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "@/lib/i18n";

const MODALITY_COLORS: Record<string, string> = {
  PET: "#e74c3c",
  MRI: "#3498db",
  EEG: "#9b59b6",
  fMRI: "#2ecc71",
  MEG: "#f39c12",
  SPECT: "#e67e22",
  PSG: "#1abc9c",
  DTI: "#3498db",
};

function ModalityBadge({ modality }: { modality: string }) {
  const color = MODALITY_COLORS[modality] ?? "var(--muted)";
  return (
    <span style={{
      display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600,
      backgroundColor: `${color}18`, color, border: `1px solid ${color}40`,
    }}>
      {modality}
    </span>
  );
}

function extractModalities(category: string | null): string[] {
  if (!category) return [];
  return category.split("/").map(s => s.trim()).filter(Boolean);
}

function formatPrice(pricing: ServiceRead["pricing"]): string {
  if (!pricing?.base_price) return "";
  return `${(pricing.base_price).toLocaleString("ko-KR")}원`;
}

export default function ServiceCatalogPage() {
  const router = useRouter();
  const { t, locale } = useTranslation();
  const [search, setSearch] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["services"],
    queryFn: listServices,
  });

  const services = (data?.items ?? []).filter(
    (s: ServiceRead) => s.status === "ACTIVE" || s.status === "PUBLISHED",
  );

  const filtered = search
    ? services.filter(
        (s: ServiceRead) =>
          s.display_name.toLowerCase().includes(search.toLowerCase()) ||
          s.name.toLowerCase().includes(search.toLowerCase()) ||
          (s.description ?? "").toLowerCase().includes(search.toLowerCase()),
      )
    : services;

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1 className="page-title">{t("serviceCatalog.title")}</h1>
          <p className="page-subtitle">
            {t("serviceCatalog.subtitle")}
          </p>
        </div>
      </header>

      <div style={{ position: "relative", maxWidth: 400, marginBottom: 24 }}>
        <MagnifyingGlass
          size={18}
          style={{ position: "absolute", left: 12, top: 10, color: "var(--muted)" }}
        />
        <input
          type="text"
          placeholder={t("serviceCatalog.searchPlaceholder")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input"
          style={{ paddingLeft: 36 }}
        />
      </div>

      {isLoading ? (
        <SkeletonCards count={6} />
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><Cube size={48} weight="light" /></div>
          <h3 className="empty-state-title">{t("serviceCatalog.noServices")}</h3>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))",
            gap: 20,
          }}
        >
          {filtered.map((svc: ServiceRead) => {
            const cc = svc.clinical_config;
            const techCount = cc?.technique_count ?? 0;
            const modalities = extractModalities(svc.category);
            const hasClinical = !!cc;

            return (
              <div key={svc.id} className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
                {/* Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                    <div style={{
                      width: 44, height: 44, borderRadius: 10,
                      background: hasClinical ? "linear-gradient(135deg, var(--primary-light), #e8f4fd)" : "var(--bg-secondary)",
                      display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                    }}>
                      {hasClinical ? <Brain size={24} style={{ color: "var(--primary)" }} /> : <Cube size={22} style={{ color: "var(--muted)" }} />}
                    </div>
                    <div>
                      <h3 style={{ fontWeight: 700, fontSize: 16, lineHeight: 1.3 }}>{svc.display_name}</h3>
                      {svc.department && (
                        <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 2 }}>{svc.department}</p>
                      )}
                    </div>
                  </div>
                  <span className="badge" style={{
                    backgroundColor: "var(--success-light)", color: "var(--success)", fontSize: 11,
                  }}>
                    {svc.status === "PUBLISHED" ? "Published" : t("common.active")}
                  </span>
                </div>

                {/* Description */}
                {svc.description && (
                  <p style={{
                    fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.6,
                    display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden",
                  }}>
                    {svc.description}
                  </p>
                )}

                {/* Modality badges + technique count */}
                <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                  {modalities.map(m => <ModalityBadge key={m} modality={m} />)}
                  {techCount > 0 && (
                    <span style={{
                      display: "inline-flex", alignItems: "center", gap: 4,
                      padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600,
                      backgroundColor: "var(--primary-light)", color: "var(--primary)",
                    }}>
                      <Lightning size={12} /> {techCount}개 분석 기법
                    </span>
                  )}
                </div>

                {/* Clinical metadata row */}
                {hasClinical && (
                  <div style={{ display: "flex", gap: 16, fontSize: 12, color: "var(--color-text-secondary)", flexWrap: "wrap" }}>
                    {cc?.fusion_method && (
                      <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        <Heartbeat size={13} style={{ color: "var(--primary)" }} />
                        {cc.fusion_method.length > 30 ? cc.fusion_method.slice(0, 30) + "..." : cc.fusion_method}
                      </span>
                    )}
                    {cc?.clinical_intent && (
                      <span>{cc.clinical_intent}</span>
                    )}
                  </div>
                )}

                {/* CTA */}
                <button
                  className="btn btn-primary"
                  style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 6, marginTop: "auto" }}
                  onClick={() => router.push(`/user/new-request?service=${svc.id}`)}
                >
                  {t("serviceCatalog.requestAnalysis")}
                  <ArrowRight size={16} />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
