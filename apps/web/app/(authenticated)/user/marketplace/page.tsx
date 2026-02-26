"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { listServices, type ServiceRead } from "@/lib/api";
import { Brain, ArrowRight, Star, ChartBar, CheckCircle, ShoppingCart } from "phosphor-react";

type Category = "All" | "MRI" | "PET" | "EEG" | "CT" | "Multi-modal";
const CATEGORIES: Category[] = ["All", "MRI", "PET", "EEG", "CT", "Multi-modal"];

function matchCategory(service: ServiceRead, cat: Category): boolean {
  if (cat === "All") return true;
  const field = (service.category ?? service.department ?? "").toLowerCase();
  return field.includes(cat.toLowerCase());
}

function ModelCard({ service, onSelect }: { service: ServiceRead; onSelect: () => void }) {
  return (
    <div className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12, cursor: "default" }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <div style={{ width: 40, height: 40, borderRadius: 8, background: "var(--primary-light)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          <Brain size={22} style={{ color: "var(--primary)" }} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontWeight: 700, fontSize: 15, marginBottom: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {service.display_name || service.name}
          </p>
          <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
            {service.category && <span className="badge badge-default">{service.category}</span>}
            <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>v{service.version_label ?? service.version}</span>
          </div>
        </div>
      </div>

      {service.description && (
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          {service.description}
        </p>
      )}

      <div style={{ display: "flex", gap: 12, fontSize: 12, color: "var(--color-text-secondary)" }}>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}><Star size={13} style={{ color: "#f59e0b" }} /> Expert validated</span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}><ChartBar size={13} /> Active</span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}><CheckCircle size={13} style={{ color: "var(--success)" }} /> Published</span>
      </div>

      <button className="btn btn-primary" style={{ width: "100%", marginTop: 4 }} onClick={onSelect}>
        Start Analysis <ArrowRight size={14} />
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
            <ShoppingCart size={28} /> AI Model Marketplace
          </h1>
          <p className="page-subtitle">Find and use expert-validated neuroimaging AI models</p>
        </div>
      </div>

      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {CATEGORIES.map(cat => (
            <button key={cat} className={`filter-tab ${category === cat ? "active" : ""}`} onClick={() => setCategory(cat)}>
              {cat}
            </button>
          ))}
        </div>
        <input className="input" placeholder="Search models..." value={search} onChange={e => setSearch(e.target.value)}
          style={{ width: 240 }} />
      </div>

      {isLoading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : services.length === 0 ? (
        <div className="empty-state">
          <Brain size={40} style={{ marginBottom: 12, opacity: 0.3 }} />
          <p className="empty-state-text">No published models found{category !== "All" ? ` in ${category}` : ""}.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>
          {services.map(service => (
            <ModelCard key={service.id} service={service}
              onSelect={() => router.push(`/user/new-request?service=${service.id}`)}
            />
          ))}
        </div>
      )}

      {services.length >= 3 && (
        <div style={{ textAlign: "center" }}>
          <button className="btn btn-secondary" onClick={() => router.push(`/user/marketplace/compare?ids=${services.slice(0, 3).map(s => s.id).join(",")}`)}>
            Compare Top Models
          </button>
        </div>
      )}
    </div>
  );
}
