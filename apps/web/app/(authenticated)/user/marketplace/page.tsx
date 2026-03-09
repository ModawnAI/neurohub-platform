"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { listServices, type ServiceRead } from "@/lib/api";
import { Brain, ArrowRight, Lightning, Heartbeat, ShoppingCart, Tag } from "phosphor-react";
import { SkeletonCards } from "@/components/skeleton";

type Category = "All" | "MRI" | "PET" | "EEG" | "fMRI" | "Multi-modal" | "PSG";
const CATEGORIES: Category[] = ["All", "Multi-modal", "PET", "MRI", "EEG", "fMRI", "PSG"];

const MODALITY_COLORS: Record<string, string> = {
  PET: "#e74c3c", MRI: "#3498db", EEG: "#9b59b6", fMRI: "#2ecc71",
  MEG: "#f39c12", SPECT: "#e67e22", PSG: "#1abc9c", DTI: "#3498db",
};

function matchCategory(service: ServiceRead, cat: Category): boolean {
  if (cat === "All") return true;
  const field = (service.category ?? service.department ?? "").toLowerCase();
  return field.includes(cat.toLowerCase());
}

function ModalityBadge({ modality }: { modality: string }) {
  const color = MODALITY_COLORS[modality] ?? "var(--muted)";
  return (
    <span style={{
      display: "inline-block", padding: "2px 7px", borderRadius: 4, fontSize: 11, fontWeight: 600,
      backgroundColor: `${color}18`, color, border: `1px solid ${color}40`,
    }}>
      {modality}
    </span>
  );
}

function ModelCard({ service, onSelect }: { service: ServiceRead; onSelect: () => void }) {
  const cc = service.clinical_config;
  const techCount = cc?.technique_count ?? 0;
  const modalities = (service.category ?? "").split("/").map(s => s.trim()).filter(Boolean);
  const hasClinical = !!cc;
  const price = service.pricing?.base_price;
  const scope = cc?.expected_diagnostic_scope ?? [];

  return (
    <div className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12, cursor: "default" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <div style={{
          width: 44, height: 44, borderRadius: 10, flexShrink: 0,
          background: hasClinical ? "linear-gradient(135deg, var(--primary-light), #e8f4fd)" : "var(--bg-secondary)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Brain size={24} style={{ color: hasClinical ? "var(--primary)" : "var(--muted)" }} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontWeight: 700, fontSize: 15, marginBottom: 2 }}>
            {service.display_name || service.name}
          </p>
          <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
            {modalities.map(m => <ModalityBadge key={m} modality={m} />)}
            <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>v{service.version_label ?? service.version}</span>
          </div>
        </div>
      </div>

      {/* Description */}
      {service.description && (
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.6, display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          {service.description}
        </p>
      )}

      {/* Clinical metadata */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", fontSize: 12 }}>
        {techCount > 0 && (
          <span style={{
            display: "inline-flex", alignItems: "center", gap: 3,
            padding: "2px 8px", borderRadius: 4, fontWeight: 600,
            backgroundColor: "var(--primary-light)", color: "var(--primary)",
          }}>
            <Lightning size={12} /> {techCount}개 기법
          </span>
        )}
        {cc?.fusion_method && (
          <span style={{
            display: "inline-flex", alignItems: "center", gap: 3,
            padding: "2px 8px", borderRadius: 4,
            backgroundColor: "#f0fdf4", color: "#16a34a",
          }}>
            <Heartbeat size={12} /> QC-가중 융합
          </span>
        )}
        <span style={{
            display: "inline-flex", alignItems: "center", gap: 3,
            padding: "2px 8px", borderRadius: 4,
            backgroundColor: "#f0fdf4", color: "#16a34a",
          }}>
            무료
          </span>
      </div>

      {/* Diagnostic scope tags */}
      {scope.length > 0 && (
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {scope.slice(0, 3).map(s => (
            <span key={s} style={{
              fontSize: 11, padding: "1px 6px", borderRadius: 3,
              backgroundColor: "var(--bg-secondary)", color: "var(--color-text-secondary)",
            }}>
              {s}
            </span>
          ))}
          {scope.length > 3 && (
            <span style={{ fontSize: 11, color: "var(--muted)" }}>+{scope.length - 3}</span>
          )}
        </div>
      )}

      <button className="btn btn-primary" style={{ width: "100%", marginTop: "auto" }} onClick={onSelect}>
        분석 시작 <ArrowRight size={14} />
      </button>
    </div>
  );
}

export default function MarketplacePage() {
  const router = useRouter();
  const [category, setCategory] = useState<Category>("All");
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["services"],
    queryFn: listServices,
  });

  const services = (data?.items ?? []).filter(s => {
    const isPublished = s.status === "PUBLISHED" || s.status === "ACTIVE";
    const matchCat = matchCategory(s, category);
    const matchSearch = !search || (s.display_name || s.name).toLowerCase().includes(search.toLowerCase()) || (s.description ?? "").toLowerCase().includes(search.toLowerCase());
    return isPublished && matchCat && matchSearch;
  });

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title" style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <ShoppingCart size={28} /> 임상 분석 서비스
          </h1>
          <p className="page-subtitle">전문가 검증을 거친 다중 모달리티 뇌영상 분석 서비스를 선택하세요</p>
        </div>
      </div>

      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {CATEGORIES.map(cat => (
            <button key={cat} className={`filter-tab ${category === cat ? "active" : ""}`} onClick={() => setCategory(cat)}>
              {cat === "All" ? "전체" : cat}
            </button>
          ))}
        </div>
        <input className="input" placeholder="서비스 검색..." value={search} onChange={e => setSearch(e.target.value)}
          style={{ width: 240 }} />
      </div>

      {isLoading ? (
        <SkeletonCards count={6} />
      ) : services.length === 0 ? (
        <div className="empty-state">
          <Brain size={40} style={{ marginBottom: 12, opacity: 0.3 }} />
          <p className="empty-state-text">
            {category !== "All" ? `${category} 카테고리에 서비스가 없습니다.` : "등록된 서비스가 없습니다."}
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 16 }}>
          {services.map(service => (
            <ModelCard key={service.id} service={service}
              onSelect={() => router.push(`/user/new-request?service=${service.id}`)}
            />
          ))}
        </div>
      )}

      {services.length >= 3 && (
        <div style={{ textAlign: "center", marginTop: 8 }}>
          <button className="btn btn-secondary" onClick={() => router.push(`/user/marketplace/compare?ids=${services.slice(0, 3).map(s => s.id).join(",")}`)}>
            서비스 비교
          </button>
        </div>
      )}
    </div>
  );
}
