"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  createGroupStudy,
  listGroupStudies,
  type GroupAnalysisType,
  type GroupStudyBrief,
} from "@/lib/api";
import { listServices, type ServiceRead } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-700",
  RUNNING: "bg-blue-100 text-blue-700",
  COMPLETED: "bg-green-100 text-green-700",
  FAILED: "bg-red-100 text-red-700",
};

const ANALYSIS_TYPES: GroupAnalysisType[] = [
  "COMPARISON",
  "CORRELATION",
  "REGRESSION",
  "LONGITUDINAL",
];

export default function GroupStudiesPage() {
  const [studies, setStudies] = useState<GroupStudyBrief[]>([]);
  const [services, setServices] = useState<ServiceRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    description: "",
    service_id: "",
    analysis_type: "COMPARISON" as GroupAnalysisType,
  });

  useEffect(() => {
    Promise.all([listGroupStudies(), listServices()])
      .then(([s, svc]) => {
        setStudies(s);
        setServices(svc.items ?? []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.service_id) {
      setError("Please select a service");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const study = await createGroupStudy({
        name: form.name,
        description: form.description || undefined,
        service_id: form.service_id,
        analysis_type: form.analysis_type,
      });
      setStudies((prev) => [{ ...study, member_count: 0 }, ...prev]);
      setShowDialog(false);
      setForm({ name: "", description: "", service_id: "", analysis_type: "COMPARISON" });
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Group Studies</h1>
          <p className="text-sm text-gray-500 mt-1">
            Compare results across multiple patient analyses
          </p>
        </div>
        <button
          onClick={() => setShowDialog(true)}
          className="btn-primary"
        >
          + New Study
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-gray-400 text-sm">Loading…</div>
      ) : studies.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          No group studies yet. Create one to get started.
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Type</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Members</th>
                <th className="px-4 py-3 text-left">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {studies.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium">{s.name}</td>
                  <td className="px-4 py-3 text-gray-500">{s.analysis_type}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[s.status] ?? ""}`}
                    >
                      {s.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{s.member_count}</td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(s.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/user/group-studies/${s.id}`}
                      className="text-blue-600 hover:underline text-xs"
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create dialog */}
      {showDialog && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
            <h2 className="text-lg font-semibold">New Group Study</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Name *</label>
                <input
                  className="input w-full"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Cortical Thickness Cohort Q1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <textarea
                  className="input w-full"
                  rows={2}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Service *</label>
                <select
                  className="input w-full"
                  required
                  value={form.service_id}
                  onChange={(e) => setForm({ ...form, service_id: e.target.value })}
                >
                  <option value="">Select a service…</option>
                  {services.map((svc) => (
                    <option key={svc.id} value={svc.id}>
                      {svc.display_name || svc.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Analysis Type *</label>
                <select
                  className="input w-full"
                  value={form.analysis_type}
                  onChange={(e) =>
                    setForm({ ...form, analysis_type: e.target.value as GroupAnalysisType })
                  }
                >
                  {ANALYSIS_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setShowDialog(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={creating}>
                  {creating ? "Creating…" : "Create Study"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
