"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Key, Copy, Check, Trash } from "phosphor-react";
import { listApiKeys, createApiKey, revokeApiKey, type ApiKeyRead } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import * as Dialog from "@radix-ui/react-dialog";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

export default function AdminApiKeysPage() {
  const { t, locale } = useTranslation();
  const dateLocale = locale === "ko" ? "ko-KR" : "en-US";
  const { user } = useAuth();
  const { addToast } = useToast();
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-keys", orgId] });
      addToast("success", t("toast.revokeSuccess"));
    },
    onError: () => addToast("error", t("toast.genericError")),
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
          <h1 className="page-title">{t("adminApiKeys.title")}</h1>
          <p className="page-subtitle">{t("adminApiKeys.subtitle")}</p>
        </div>
        <div className="page-header-actions">
          <Dialog.Root open={showCreate} onOpenChange={(open) => { setShowCreate(open); if (!open) setNewKey(null); }}>
            <Dialog.Trigger asChild>
              <button className="btn btn-primary">
                <Key size={16} /> {t("adminApiKeys.generateNew")}
              </button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="dialog-overlay" />
              <Dialog.Content className="dialog-content">
                <Dialog.Title className="dialog-title">{t("adminApiKeys.newKeyTitle")}</Dialog.Title>

                {newKey ? (
                  <div className="stack-md">
                    <div className="banner banner-warning">
                      {t("adminApiKeys.keyWarning")}
                    </div>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <input className="input mono-field" value={newKey} readOnly style={{ flex: 1, fontSize: 12 }} />
                      <button className="btn btn-sm btn-secondary" onClick={handleCopy}>
                        {copied ? <Check size={14} /> : <Copy size={14} />}
                      </button>
                    </div>
                    <button className="btn btn-primary" onClick={() => { setShowCreate(false); setNewKey(null); }}>
                      {t("common.confirm")}
                    </button>
                  </div>
                ) : (
                  <div className="stack-md">
                    <label className="field">
                      {t("adminApiKeys.keyName")}
                      <input className="input" value={keyName} onChange={(e) => setKeyName(e.target.value)} placeholder={t("adminApiKeys.keyNamePlaceholder")} />
                    </label>
                    <label className="field">
                      {t("adminApiKeys.expiryDays")}
                      <input className="input" type="number" value={expiryDays} onChange={(e) => setExpiryDays(Number(e.target.value))} min={1} max={365} />
                    </label>
                    <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                      <Dialog.Close asChild>
                        <button className="btn btn-secondary">{t("common.cancel")}</button>
                      </Dialog.Close>
                      <button className="btn btn-primary" onClick={() => createMut.mutate()} disabled={!keyName.trim() || createMut.isPending}>
                        {createMut.isPending ? <span className="spinner" /> : t("common.generate")}
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
                  <th>{t("adminApiKeys.tableName")}</th>
                  <th>{t("adminApiKeys.tablePrefix")}</th>
                  <th>{t("adminApiKeys.tableStatus")}</th>
                  <th>{t("adminApiKeys.tableExpiry")}</th>
                  <th>{t("adminApiKeys.tableLastUsed")}</th>
                  <th>{t("adminApiKeys.tableCreatedDate")}</th>
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
                        {k.status === "ACTIVE" ? t("common.active") : t("adminApiKeys.revoked")}
                      </span>
                    </td>
                    <td>{k.expires_at ? new Date(k.expires_at).toLocaleDateString(dateLocale) : "-"}</td>
                    <td>{k.last_used_at ? new Date(k.last_used_at).toLocaleString(dateLocale) : "-"}</td>
                    <td>{new Date(k.created_at).toLocaleDateString(dateLocale)}</td>
                    <td>
                      {k.status === "ACTIVE" && (
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => { if (confirm(t("confirmDialog.revokeKeyTitle"))) revokeMut.mutate(k.id); }}
                          disabled={revokeMut.isPending}
                        >
                          <Trash size={14} /> {t("common.revoke")}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {keys.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: "center", padding: 24, color: "var(--muted)" }}>
                      {t("adminApiKeys.noKeys")}
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
