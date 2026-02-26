"use client";

import { useState, useEffect, useCallback } from "react";
import {
  listDicomStudies,
  linkDicomStudy,
  createRequestFromDicom,
  type DicomStudyRead,
} from "@/lib/api";

const STATUS_TABS = ["All", "RECEIVING", "RECEIVED", "LINKED", "FAILED"] as const;
type StatusTab = (typeof STATUS_TABS)[number];

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    RECEIVING: "bg-yellow-100 text-yellow-800",
    RECEIVED: "bg-blue-100 text-blue-800",
    LINKED: "bg-green-100 text-green-800",
    FAILED: "bg-red-100 text-red-800",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors[status] ?? "bg-gray-100 text-gray-700"}`}>
      {status}
    </span>
  );
}

export default function DicomGatewayPage() {
  const [studies, setStudies] = useState<DicomStudyRead[]>([]);
  const [total, setTotal] = useState(0);
  const [activeTab, setActiveTab] = useState<StatusTab>("All");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Link modal state
  const [linkStudy, setLinkStudy] = useState<DicomStudyRead | null>(null);
  const [linkRequestId, setLinkRequestId] = useState("");
  const [linkLoading, setLinkLoading] = useState(false);

  // Create request modal state
  const [createStudy, setCreateStudy] = useState<DicomStudyRead | null>(null);
  const [createServiceId, setCreateServiceId] = useState("");
  const [createLoading, setCreateLoading] = useState(false);

  const fetchStudies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = activeTab !== "All" ? { status: activeTab } : undefined;
      const data = await listDicomStudies(params);
      setStudies(data.items);
      setTotal(data.total);
    } catch (e: any) {
      setError(e.message || "Failed to load studies");
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchStudies();
  }, [fetchStudies]);

  const handleLink = async () => {
    if (!linkStudy || !linkRequestId.trim()) return;
    setLinkLoading(true);
    try {
      await linkDicomStudy(linkStudy.study_instance_uid, linkRequestId.trim());
      setLinkStudy(null);
      setLinkRequestId("");
      await fetchStudies();
    } catch (e: any) {
      alert("Link failed: " + (e.message || String(e)));
    } finally {
      setLinkLoading(false);
    }
  };

  const handleCreateRequest = async () => {
    if (!createStudy || !createServiceId.trim()) return;
    setCreateLoading(true);
    try {
      await createRequestFromDicom(createStudy.study_instance_uid, createServiceId.trim());
      setCreateStudy(null);
      setCreateServiceId("");
      await fetchStudies();
    } catch (e: any) {
      alert("Create request failed: " + (e.message || String(e)));
    } finally {
      setCreateLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">DICOM Gateway</h1>
        <p className="text-sm text-gray-500 mt-1">
          Incoming DICOM studies from PACS systems via STOW-RS
        </p>
      </div>

      {/* Status tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab}
          </button>
        ))}
        <div className="ml-auto flex items-center text-sm text-gray-400">
          {total} studies
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading…</div>
      ) : studies.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No studies found.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase tracking-wide border-b">
                <th className="py-2 pr-4">Study UID</th>
                <th className="py-2 pr-4">Patient</th>
                <th className="py-2 pr-4">Date</th>
                <th className="py-2 pr-4">Modality</th>
                <th className="py-2 pr-4">Series</th>
                <th className="py-2 pr-4">Instances</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Source AET</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {studies.map((s) => (
                <tr key={s.id} className="border-b hover:bg-gray-50">
                  <td className="py-2 pr-4 font-mono text-xs max-w-[160px] truncate" title={s.study_instance_uid}>
                    {s.study_instance_uid.slice(-12)}…
                  </td>
                  <td className="py-2 pr-4">
                    <div className="font-medium">{s.patient_name || "—"}</div>
                    <div className="text-xs text-gray-400">{s.patient_id}</div>
                  </td>
                  <td className="py-2 pr-4">{s.study_date || "—"}</td>
                  <td className="py-2 pr-4">{s.modality || "—"}</td>
                  <td className="py-2 pr-4">{s.num_series}</td>
                  <td className="py-2 pr-4">{s.num_instances}</td>
                  <td className="py-2 pr-4">
                    <StatusBadge status={s.status} />
                  </td>
                  <td className="py-2 pr-4 text-xs text-gray-500">{s.source_aet || "—"}</td>
                  <td className="py-2">
                    <div className="flex gap-2">
                      {s.status !== "LINKED" && (
                        <>
                          <button
                            onClick={() => { setLinkStudy(s); setLinkRequestId(""); }}
                            className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-100"
                          >
                            Link
                          </button>
                          <button
                            onClick={() => { setCreateStudy(s); setCreateServiceId(""); }}
                            className="text-xs px-2 py-1 rounded border border-blue-300 text-blue-600 hover:bg-blue-50"
                          >
                            Create Request
                          </button>
                        </>
                      )}
                      {s.request_id && (
                        <span className="text-xs text-green-600">Linked</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Link to Request Modal */}
      {linkStudy && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold mb-4">Link Study to Request</h2>
            <p className="text-sm text-gray-500 mb-4">
              Study: <span className="font-mono">{linkStudy.study_instance_uid.slice(-20)}</span>
            </p>
            <label className="block text-sm font-medium mb-1">Request ID (UUID)</label>
            <input
              type="text"
              value={linkRequestId}
              onChange={(e) => setLinkRequestId(e.target.value)}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              className="w-full border rounded px-3 py-2 text-sm font-mono mb-4"
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => setLinkStudy(null)} className="px-4 py-2 text-sm border rounded">
                Cancel
              </button>
              <button
                onClick={handleLink}
                disabled={linkLoading || !linkRequestId.trim()}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded disabled:opacity-50"
              >
                {linkLoading ? "Linking…" : "Link"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Request Modal */}
      {createStudy && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold mb-4">Create Request from DICOM Study</h2>
            <p className="text-sm text-gray-500 mb-1">
              Patient: <strong>{createStudy.patient_name || createStudy.patient_id}</strong>
            </p>
            <p className="text-sm text-gray-500 mb-4">
              Modality: {createStudy.modality} · {createStudy.num_instances} instances
            </p>
            <label className="block text-sm font-medium mb-1">Service ID (UUID)</label>
            <input
              type="text"
              value={createServiceId}
              onChange={(e) => setCreateServiceId(e.target.value)}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              className="w-full border rounded px-3 py-2 text-sm font-mono mb-4"
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => setCreateStudy(null)} className="px-4 py-2 text-sm border rounded">
                Cancel
              </button>
              <button
                onClick={handleCreateRequest}
                disabled={createLoading || !createServiceId.trim()}
                className="px-4 py-2 text-sm bg-green-600 text-white rounded disabled:opacity-50"
              >
                {createLoading ? "Creating…" : "Create Request"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
