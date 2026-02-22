"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Key, Copy, Check, Trash } from "phosphor-react";
import { listApiKeys, createApiKey, revokeApiKey, type ApiKeyRead } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import * as Dialog from "@radix-ui/react-dialog";

export default function AdminApiKeysPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const orgId = user?.institutionId;

  const [showCreate, setShowCreate] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [expiryDays, setExpiryDays] = useState(90);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["api-keys", orgId],
    queryFn: () => listApiKeys(orgId!),
    enabled: !!orgId,
  });

  const createMut = useMutation({
    mutationFn: () => createApiKey(orgId!, { name: keyName, expires_in_days: expiryDays }),
    onSuccess: (result) => {
      setNewKey(result.api_key);
      setKeyName("");
      queryClient.invalidateQueries({ queryKey: ["api-keys", orgId] });
    },
  });

  const revokeMut = useMutation({
    mutationFn: (keyId: string) => revokeApiKey(orgId!, keyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["api-keys", orgId] }),
  });

  function handleCopy() {
    if (newKey) {
      navigator.clipboard.writeText(newKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  const keys = data?.items ?? [];

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">API 키 관리</h1>
          <p className="page-subtitle">B2B 연동을 위한 API 키를 관리합니다</p>
        </div>
        <div className="page-header-actions">
          <Dialog.Root open={showCreate} onOpenChange={(open) => { setShowCreate(open); if (!open) setNewKey(null); }}>
            <Dialog.Trigger asChild>
              <button className="btn btn-primary">
                <Key size={16} /> 새 키 생성
              </button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="dialog-overlay" />
              <Dialog.Content className="dialog-content">
                <Dialog.Title className="dialog-title">새 API 키 생성</Dialog.Title>

                {newKey ? (
                  <div className="stack-md">
                    <div className="banner banner-warning">
                      이 키는 한 번만 표시됩니다. 안전한 곳에 저장하세요.
                    </div>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <input className="input mono-field" value={newKey} readOnly style={{ flex: 1, fontSize: 12 }} />
                      <button className="btn btn-sm btn-secondary" onClick={handleCopy}>
                        {copied ? <Check size={14} /> : <Copy size={14} />}
                      </button>
                    </div>
                    <button className="btn btn-primary" onClick={() => { setShowCreate(false); setNewKey(null); }}>
                      확인
                    </button>
                  </div>
                ) : (
                  <div className="stack-md">
                    <label className="field">
                      키 이름
                      <input className="input" value={keyName} onChange={(e) => setKeyName(e.target.value)} placeholder="예: 연동 서버 A" />
                    </label>
                    <label className="field">
                      만료 기간 (일)
                      <input className="input" type="number" value={expiryDays} onChange={(e) => setExpiryDays(Number(e.target.value))} min={1} max={365} />
                    </label>
                    <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                      <Dialog.Close asChild>
                        <button className="btn btn-secondary">취소</button>
                      </Dialog.Close>
                      <button className="btn btn-primary" onClick={() => createMut.mutate()} disabled={!keyName.trim() || createMut.isPending}>
                        {createMut.isPending ? <span className="spinner" /> : "생성"}
                      </button>
                    </div>
                  </div>
                )}
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : (
        <div className="panel">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>이름</th>
                  <th>접두사</th>
                  <th>상태</th>
                  <th>만료일</th>
                  <th>마지막 사용</th>
                  <th>생성일</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {keys.map((k: ApiKeyRead) => (
                  <tr key={k.id}>
                    <td style={{ fontWeight: 600 }}>{k.name}</td>
                    <td className="mono-cell">{k.key_prefix}...</td>
                    <td>
                      <span className={`status-chip ${k.status === "ACTIVE" ? "status-final" : "status-cancelled"}`}>
                        {k.status === "ACTIVE" ? "활성" : "폐기"}
                      </span>
                    </td>
                    <td>{k.expires_at ? new Date(k.expires_at).toLocaleDateString("ko-KR") : "-"}</td>
                    <td>{k.last_used_at ? new Date(k.last_used_at).toLocaleString("ko-KR") : "-"}</td>
                    <td>{new Date(k.created_at).toLocaleDateString("ko-KR")}</td>
                    <td>
                      {k.status === "ACTIVE" && (
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => revokeMut.mutate(k.id)}
                          disabled={revokeMut.isPending}
                        >
                          <Trash size={14} /> 폐기
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {keys.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: "center", padding: 24, color: "var(--muted)" }}>
                      등록된 API 키가 없습니다.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
