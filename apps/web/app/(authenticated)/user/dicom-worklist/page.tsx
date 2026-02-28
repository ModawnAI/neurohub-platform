"use client";

import { useState, useEffect, useCallback } from "react";
import { listDicomStudies, type DicomStudyRead } from "@/lib/api";
import { useT } from "@/lib/i18n";

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    RECEIVING: "bg-yellow-100 text-yellow-800",
    RECEIVED: "bg-blue-100 text-blue-800",
    LINKED: "bg-green-100 text-green-800",
    FAILED: "bg-red-100 text-red-800",
  };
  const t = useT();
  const labelMap: Record<string, string> = {
    RECEIVING: t("dicom.statusReceiving"),
    RECEIVED: t("dicom.statusReceived"),
    LINKED: t("dicom.statusLinked"),
    FAILED: t("dicom.statusFailed"),
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors[status] ?? "bg-gray-100 text-gray-700"}`}>
      {labelMap[status] ?? status}
    </span>
  );
}

export default function DicomWorklistPage() {
  const t = useT();
  const [studies, setStudies] = useState<DicomStudyRead[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [modality, setModality] = useState("");

  const fetchStudies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (modality) params.modality = modality;
      const data = await listDicomStudies(Object.keys(params).length ? params : undefined);
      setStudies(data.items);
      setTotal(data.total);
    } catch (e: any) {
      setError(e.message || t("dicom.loadError"));
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, modality, t]);

  useEffect(() => {
    fetchStudies();
  }, [fetchStudies]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t("dicom.worklistTitle")}</h1>
        <p className="text-sm text-gray-500 mt-1">
          {t("dicom.worklistSubtitle")}
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 p-4 bg-gray-50 rounded-lg">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">{t("dicom.filterFrom")}</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">{t("dicom.filterTo")}</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">{t("dicom.filterModality")}</label>
          <select
            value={modality}
            onChange={(e) => setModality(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          >
            <option value="">{t("dicom.tabAll")}</option>
            <option value="MR">MR</option>
            <option value="CT">CT</option>
            <option value="PET">PET</option>
            <option value="US">US</option>
            <option value="XR">XR</option>
          </select>
        </div>
        <div className="flex items-end">
          <button
            onClick={() => { setDateFrom(""); setDateTo(""); setModality(""); }}
            className="px-3 py-1 text-sm border rounded hover:bg-gray-100"
          >
            {t("dicom.filterClear")}
          </button>
        </div>
        <div className="flex items-end ml-auto text-sm text-gray-400">
          {t("dicom.studyCount").replace("{count}", String(total))}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-400">{t("dicom.loading")}</div>
      ) : studies.length === 0 ? (
        <div className="text-center py-12 text-gray-400">{t("dicom.noStudies")}</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase tracking-wide border-b">
                <th className="py-2 pr-4">{t("dicom.patient")}</th>
                <th className="py-2 pr-4">{t("dicom.studyDate")}</th>
                <th className="py-2 pr-4">{t("dicom.modality")}</th>
                <th className="py-2 pr-4">{t("dicom.description")}</th>
                <th className="py-2 pr-4">{t("dicom.seriesInstances")}</th>
                <th className="py-2 pr-4">{t("common.status")}</th>
                <th className="py-2">{t("dicom.request")}</th>
              </tr>
            </thead>
            <tbody>
              {studies.map((s) => (
                <tr key={s.id} className="border-b hover:bg-gray-50">
                  <td className="py-2 pr-4">
                    <div className="font-medium">{s.patient_name || "—"}</div>
                    <div className="text-xs text-gray-400">{s.patient_id}</div>
                  </td>
                  <td className="py-2 pr-4">{s.study_date || "—"}</td>
                  <td className="py-2 pr-4">{s.modality || "—"}</td>
                  <td className="py-2 pr-4 max-w-[200px] truncate" title={s.study_description ?? undefined}>
                    {s.study_description || "—"}
                  </td>
                  <td className="py-2 pr-4">
                    {s.num_series} / {s.num_instances}
                  </td>
                  <td className="py-2 pr-4">
                    <StatusBadge status={s.status} />
                  </td>
                  <td className="py-2">
                    {s.request_id ? (
                      <a
                        href={`/user/requests?id=${s.request_id}`}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        {t("dicom.viewRequest")}
                      </a>
                    ) : (
                      <span className="text-xs text-gray-400">{t("dicom.notLinked")}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
