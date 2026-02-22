"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { getUsage, getAdminStats, type UsageEntry } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

function getMonthRange(monthsAgo = 0, dateLocale = "ko-KR") {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth() - monthsAgo, 1);
  const end = new Date(now.getFullYear(), now.getMonth() - monthsAgo + 1, 0);
  return {
    start: start.toISOString().split("T")[0]!,
    end: end.toISOString().split("T")[0]!,
    label: start.toLocaleDateString(dateLocale, { year: "numeric", month: "long" }),
  };
}

export default function AdminSettingsPage() {
  const { t, locale } = useTranslation();
  const dateLocale = locale === "ko" ? "ko-KR" : "en-US";
  const { user } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState(0);
  const monthRange = getMonthRange(selectedMonth, dateLocale);

  const { data: stats } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: getAdminStats,
  });

  const { data: usageData, isLoading: usageLoading } = useQuery({
    queryKey: ["billing-usage", monthRange.start, monthRange.end],
    queryFn: () => getUsage(monthRange.start, monthRange.end),
  });

  const usageItems: UsageEntry[] = usageData?.items ?? [];

  return (
    <div className="stack-lg">
      <h1 className="page-title">{t("adminSettings.title")}</h1>

      <div className="panel">
        <h2 className="panel-title-mb">{t("adminSettings.adminInfo")}</h2>
        <div className="stack-md">
          <div>
            <p className="detail-label">{t("auth.email")}</p>
            <p className="detail-value">{user?.email || "-"}</p>
          </div>
          <div>
            <p className="detail-label">{t("auth.name")}</p>
            <p className="detail-value">{user?.displayName || "-"}</p>
          </div>
          <div>
            <p className="detail-label">{t("adminUsers.fieldOrg")}</p>
            <p className="detail-value">{user?.institutionName || "-"}</p>
          </div>
        </div>
      </div>

      <div className="panel">
        <h2 className="panel-title-mb">{t("adminSettings.systemInfo")}</h2>
        <div className="stack-md">
          <div>
            <p className="detail-label">{t("adminSettings.platform")}</p>
            <p className="detail-value">NeuroHub {process.env.NEXT_PUBLIC_APP_VERSION || "v1.0"}</p>
          </div>
          <div>
            <p className="detail-label">{t("adminSettings.environment")}</p>
            <p className="detail-value">{process.env.NEXT_PUBLIC_ENV || process.env.NODE_ENV || "development"}</p>
          </div>
          {stats && (
            <>
              <div>
                <p className="detail-label">{t("adminSettings.totalRequests")}</p>
                <p className="detail-value">{stats.total_requests}{t("common.unitCount")}</p>
              </div>
              <div>
                <p className="detail-label">{t("adminSettings.activeUsers")}</p>
                <p className="detail-value">{stats.active_users}{t("common.unitPeople")}</p>
              </div>
              <div>
                <p className="detail-label">{t("adminSettings.registeredServices")}</p>
                <p className="detail-value">{stats.total_services}{t("common.unitItems")}</p>
              </div>
              <div>
                <p className="detail-label">{t("adminSettings.registeredOrgs")}</p>
                <p className="detail-value">{stats.total_organizations}{t("common.unitItems")}</p>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 className="panel-title" style={{ margin: 0 }}>{t("adminSettings.usage")}</h2>
          <div style={{ display: "flex", gap: 8 }}>
            {[0, 1, 2].map((m) => {
              const mr = getMonthRange(m, dateLocale);
              return (
                <button
                  key={m}
                  className={`btn btn-sm ${selectedMonth === m ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => setSelectedMonth(m)}
                >
                  {mr.label}
                </button>
              );
            })}
          </div>
        </div>

        {usageLoading ? (
          <div className="loading-center"><span className="spinner" /></div>
        ) : usageItems.length === 0 ? (
          <p className="muted-text">{t("adminSettings.noUsageData").replace("{month}", monthRange.label)}</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("adminSettings.tableService")}</th>
                  <th>{t("adminSettings.tableType")}</th>
                  <th>{t("adminSettings.tableCount")}</th>
                  <th>{t("adminSettings.tableTotal")}</th>
                </tr>
              </thead>
              <tbody>
                {usageItems.map((item, i) => (
                  <tr key={i}>
                    <td>{item.service_name}</td>
                    <td>{item.charge_type}</td>
                    <td>{item.count}{t("common.unitCount")}</td>
                    <td style={{ fontWeight: 600 }}>{t("adminSettings.currencyFormat").replace("{amount}", item.total_amount.toLocaleString(dateLocale))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
