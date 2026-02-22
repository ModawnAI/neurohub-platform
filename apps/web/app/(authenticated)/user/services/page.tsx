"use client";

import { listServices, type ServiceRead } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { MagnifyingGlass, Cube, ArrowRight } from "phosphor-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useT } from "@/lib/i18n";

export default function ServiceCatalogPage() {
  const router = useRouter();
  const t = useT();
  const [search, setSearch] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["services"],
    queryFn: listServices,
  });

  const services = (data?.items ?? []).filter(
    (s: ServiceRead) => s.status === "ACTIVE",
  );

  const filtered = search
    ? services.filter(
        (s: ServiceRead) =>
          s.display_name.toLowerCase().includes(search.toLowerCase()) ||
          s.name.toLowerCase().includes(search.toLowerCase()),
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
        <p style={{ color: "var(--muted)" }}>{t("common.loading")}</p>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <Cube size={48} />
          <p>{t("serviceCatalog.noServices")}</p>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
            gap: 16,
          }}
        >
          {filtered.map((svc: ServiceRead) => (
            <div key={svc.id} className="panel" style={{ padding: 20 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  marginBottom: 12,
                }}
              >
                <div>
                  <h3 style={{ fontWeight: 600, fontSize: 16 }}>
                    {svc.display_name}
                  </h3>
                  <p
                    style={{
                      color: "var(--muted)",
                      fontSize: 13,
                      marginTop: 2,
                    }}
                  >
                    {svc.name} v{svc.version}
                  </p>
                </div>
                <span
                  className="badge"
                  style={{
                    backgroundColor: "var(--success-light)",
                    color: "var(--success)",
                  }}
                >
                  {t("common.active")}
                </span>
              </div>

              {svc.department && (
                <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 12 }}>
                  {t("serviceCatalog.department")} {svc.department}
                </p>
              )}

              <p style={{ color: "var(--muted)", fontSize: 13, marginBottom: 16 }}>
                {t("serviceCatalog.createdDate")} {new Date(svc.created_at).toLocaleDateString("ko-KR")}
              </p>

              <button
                className="btn btn-primary"
                style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}
                onClick={() => router.push("/user/new-request")}
              >
                {t("serviceCatalog.requestAnalysis")}
                <ArrowRight size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
