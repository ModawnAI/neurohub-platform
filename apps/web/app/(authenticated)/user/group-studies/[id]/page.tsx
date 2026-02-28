"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getGroupStudy,
  addStudyMember,
  removeStudyMember,
  runGroupAnalysis,
  type GroupStudyRead,
  type GroupStudyMemberRead,
} from "@/lib/api";
import { listRequests, type RequestRead } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-700",
  RUNNING: "bg-blue-100 text-blue-700",
  COMPLETED: "bg-green-100 text-green-700",
  FAILED: "bg-red-100 text-red-700",
};

export default function GroupStudyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [study, setStudy] = useState<GroupStudyRead | null>(null);
  const [requests, setRequests] = useState<RequestRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddMember, setShowAddMember] = useState(false);
  const [addForm, setAddForm] = useState({ request_id: "", group_label: "default" });
  const [addingMember, setAddingMember] = useState(false);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    Promise.all([getGroupStudy(id), listRequests()])
      .then(([s, r]) => {
        setStudy(s);
        // Filter for completed requests
        setRequests((r.items ?? []).filter((req: RequestRead) => req.status === "FINAL"));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleAddMember(e: React.FormEvent) {
    e.preventDefault();
    if (!addForm.request_id) return;
    setAddingMember(true);
    setError(null);
    try {
      const updated = await addStudyMember(id, {
        request_id: addForm.request_id,
        group_label: addForm.group_label || "default",
      });
      setStudy(updated);
      setShowAddMember(false);
      setAddForm({ request_id: "", group_label: "default" });
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setAddingMember(false);
    }
  }

  async function handleRemoveMember(member: GroupStudyMemberRead) {
    if (!confirm("Remove this member from the study?")) return;
    try {
      await removeStudyMember(id, member.request_id);
      setStudy((prev) =>
        prev ? { ...prev, members: prev.members.filter((m) => m.id !== member.id) } : prev,
      );
    } catch (e: unknown) {
      setError((e as Error).message);
    }
  }

  async function handleRunAnalysis() {
    if (!confirm("Run group analysis? This will aggregate all member results.")) return;
    setRunning(true);
    setError(null);
    try {
      const updated = await runGroupAnalysis(id);
      setStudy(updated);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  if (loading) return <div className="text-gray-400 text-sm p-6">Loading…</div>;
  if (error && !study) return <div className="text-red-600 p-6">{error}</div>;
  if (!study) return null;

  const result = study.result as Record<string, unknown> | null;
  const groups = result?.groups as Array<{
    label: string;
    n: number;
    metrics: Record<string, { mean: number | null; std: number | null; n: number }>;
  }> | undefined;
  const statTests = result?.statistical_tests as Array<{
    name: string;
    p_value: number | null;
    effect_size: number | null;
  }> | undefined;
  const summary = result?.summary as Record<string, unknown> | undefined;
  const allMetrics = groups ? Array.from(new Set(groups.flatMap((g) => Object.keys(g.metrics)))) : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link href="/user/group-studies" className="text-sm text-gray-500 hover:underline">
            ← Group Studies
          </Link>
          <h1 className="text-2xl font-bold mt-1">{study.name}</h1>
          {study.description && <p className="text-gray-500 text-sm mt-1">{study.description}</p>}
          <div className="flex gap-2 mt-2 items-center">
            <span
              className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[study.status] ?? ""}`}
            >
              {study.status}
            </span>
            <span className="text-xs text-gray-400">{study.analysis_type}</span>
          </div>
        </div>
        <button
          onClick={handleRunAnalysis}
          disabled={study.members.length < 2 || running || study.status === "RUNNING"}
          className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {running ? "Running…" : "Run Analysis"}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Members */}
      <div className="card">
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <h2 className="font-semibold">Members ({study.members.length})</h2>
          <button onClick={() => setShowAddMember(true)} className="btn-secondary text-sm">
            + Add Request
          </button>
        </div>
        {study.members.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">
            No members yet. Add completed requests to begin.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wide">
              <tr>
                <th className="px-4 py-2 text-left">Request ID</th>
                <th className="px-4 py-2 text-left">Group Label</th>
                <th className="px-4 py-2 text-left">Added</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {study.members.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs text-gray-600">
                    {m.request_id.slice(0, 8)}…
                  </td>
                  <td className="px-4 py-2">
                    <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">
                      {m.group_label}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-400 text-xs">
                    {new Date(m.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => handleRemoveMember(m)}
                      className="text-red-400 hover:text-red-600 text-xs"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Results */}
      {study.status === "COMPLETED" && Boolean(result) && (
        <div className="space-y-4">
          {/* Summary */}
          {summary && (
            <div className="card p-4">
              <h2 className="font-semibold mb-3">Summary</h2>
              <dl className="grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
                {Object.entries(summary).map(([k, v]) => (
                  <div key={k} className="bg-gray-50 rounded p-2">
                    <dt className="text-xs text-gray-400 capitalize">{k.replace(/_/g, " ")}</dt>
                    <dd className="font-medium mt-0.5">
                      {Array.isArray(v) ? (v as unknown[]).join(", ") : String(v)}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          )}

          {/* Group metrics table */}
          {groups && groups.length > 0 && allMetrics.length > 0 && (
            <div className="card overflow-auto">
              <h2 className="font-semibold p-4 border-b border-gray-100">Group Metrics</h2>
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs uppercase tracking-wide text-gray-600">
                  <tr>
                    <th className="px-4 py-2 text-left">Metric</th>
                    {groups.map((g) => (
                      <th key={g.label} className="px-4 py-2 text-left" colSpan={2}>
                        {g.label} (n={g.n})
                      </th>
                    ))}
                  </tr>
                  <tr>
                    <th className="px-4 py-2" />
                    {groups.map((g) => (
                      <>
                        <th key={`${g.label}-mean`} className="px-3 py-1 text-left font-normal text-gray-500">Mean</th>
                        <th key={`${g.label}-std`} className="px-3 py-1 text-left font-normal text-gray-500">Std</th>
                      </>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {allMetrics.map((metric) => (
                    <tr key={metric} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-xs text-gray-600 max-w-xs truncate">
                        {metric}
                      </td>
                      {groups.map((g) => {
                        const m = g.metrics[metric];
                        return (
                          <>
                            <td key={`${g.label}-${metric}-mean`} className="px-3 py-2 text-gray-700">
                              {m?.mean != null ? m.mean.toFixed(4) : "—"}
                            </td>
                            <td key={`${g.label}-${metric}-std`} className="px-3 py-2 text-gray-400">
                              {m?.std != null ? m.std.toFixed(4) : "—"}
                            </td>
                          </>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Statistical tests */}
          {statTests && statTests.length > 0 && (
            <div className="card overflow-auto">
              <h2 className="font-semibold p-4 border-b border-gray-100">Statistical Tests</h2>
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs uppercase tracking-wide text-gray-600">
                  <tr>
                    <th className="px-4 py-2 text-left">Test</th>
                    <th className="px-4 py-2 text-left">p-value</th>
                    <th className="px-4 py-2 text-left">Effect Size (d)</th>
                    <th className="px-4 py-2 text-left">Significance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {statTests.map((t, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-xs text-gray-600 max-w-sm truncate">{t.name}</td>
                      <td className="px-4 py-2">{t.p_value != null ? t.p_value.toFixed(4) : "—"}</td>
                      <td className="px-4 py-2">
                        {t.effect_size != null ? t.effect_size.toFixed(3) : "—"}
                      </td>
                      <td className="px-4 py-2">
                        {t.p_value != null ? (
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-xs ${
                              t.p_value < 0.01
                                ? "bg-green-100 text-green-700"
                                : t.p_value < 0.05
                                  ? "bg-yellow-100 text-yellow-700"
                                  : "bg-gray-100 text-gray-500"
                            }`}
                          >
                            {t.p_value < 0.01 ? "p<0.01" : t.p_value < 0.05 ? "p<0.05" : "n.s."}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {study.status === "FAILED" && Boolean(result?.error) && (
        <div className="card p-4 bg-red-50 border border-red-200">
          <p className="text-sm text-red-700 font-medium">Analysis failed</p>
          <p className="text-sm text-red-500 mt-1">{String(result?.error)}</p>
        </div>
      )}

      {/* Add member dialog */}
      {showAddMember && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
            <h2 className="text-lg font-semibold">Add Request to Study</h2>
            <form onSubmit={handleAddMember} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Request *</label>
                <select
                  className="input w-full"
                  required
                  value={addForm.request_id}
                  onChange={(e) => setAddForm({ ...addForm, request_id: e.target.value })}
                >
                  <option value="">Select a completed request…</option>
                  {requests.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.id.slice(0, 8)}… — {r.status}
                      {r.service_snapshot
                        ? ` (${(r.service_snapshot as { display_name?: string }).display_name ?? ""})`
                        : ""}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Group Label</label>
                <input
                  className="input w-full"
                  value={addForm.group_label}
                  onChange={(e) => setAddForm({ ...addForm, group_label: e.target.value })}
                  placeholder="e.g. control, treatment, group_A"
                />
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddMember(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={addingMember}>
                  {addingMember ? "Adding…" : "Add Member"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
