"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { updateProfile } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

export default function ExpertSettingsPage() {
  const { user, refreshUser } = useAuth();
  const { t } = useTranslation();
  const { addToast } = useToast();
  const [displayName, setDisplayName] = useState(user?.displayName || "");
  const [specialization, setSpecialization] = useState(user?.specialization || "");
  const [bio, setBio] = useState("");

  const updateMut = useMutation({
    mutationFn: () => updateProfile({
      display_name: displayName,
      specialization: specialization || undefined,
      bio: bio || undefined,
    }),
    onSuccess: () => {
      refreshUser();
      addToast("success", t("toast.saveSuccess"));
    },
    onError: () => addToast("error", t("toast.saveError")),
  });

  return (
    <div className="stack-lg">
      <h1 className="page-title">{t("expertSettings.title")}</h1>

      <div className="panel">
        <h2 className="panel-title-mb">{t("expertSettings.profile")}</h2>
        <div className="auth-form">
          <label className="field">
            {t("expertSettings.email")}
            <input className="input" value={user?.email || ""} disabled style={{ opacity: 0.6 }} />
          </label>
          <label className="field">
            {t("expertSettings.displayName")}
            <input className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </label>
          <label className="field">
            {t("expertSettings.specialization")}
            <input className="input" value={specialization} onChange={(e) => setSpecialization(e.target.value)} placeholder={t("expertSettings.specializationPlaceholder")} />
          </label>
          <label className="field">
            {t("expertSettings.bio")}
            <textarea className="textarea" value={bio} onChange={(e) => setBio(e.target.value)} placeholder={t("expertSettings.bioPlaceholder")} rows={3} />
          </label>
          <button className="btn btn-primary" onClick={() => updateMut.mutate()} disabled={updateMut.isPending}>
            {updateMut.isPending ? <span className="spinner" /> : t("expertSettings.save")}
          </button>
        </div>
      </div>

      <div className="panel">
        <h2 className="panel-title-mb">{t("expertSettings.expertStatus")}</h2>
        {user?.expertStatus === "APPROVED" ? (
          <div className="banner banner-success">{t("expertSettings.statusApproved")}</div>
        ) : user?.expertStatus === "PENDING_APPROVAL" ? (
          <div className="banner banner-warning">{t("expertSettings.statusPending")}</div>
        ) : (
          <div className="banner banner-info">{t("expertSettings.statusOther")}</div>
        )}
      </div>
    </div>
  );
}
