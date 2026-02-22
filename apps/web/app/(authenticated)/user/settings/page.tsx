"use client";

import { useMutation } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { updateProfile } from "@/lib/api";
import { useZodForm } from "@/lib/use-zod-form";
import { profileUpdateSchema, type ProfileUpdateValues } from "@/lib/schemas";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

export default function UserSettingsPage() {
  const { user, refreshUser } = useAuth();
  const { t } = useTranslation();
  const { addToast } = useToast();

  const { values, errors, setField, validate } = useZodForm<ProfileUpdateValues>(profileUpdateSchema, {
    display_name: user?.displayName || "",
    phone: "",
  });

  const updateMut = useMutation({
    mutationFn: () => {
      const data = validate();
      if (!data) throw new Error(t("common.validationError"));
      return updateProfile({ display_name: data.display_name, phone: data.phone || undefined });
    },
    onSuccess: () => {
      refreshUser();
      addToast("success", t("toast.saveSuccess"));
    },
    onError: () => addToast("error", t("toast.saveError")),
  });

  return (
    <div className="stack-lg">
      <h1 className="page-title">{t("userSettings.title")}</h1>

      <div className="panel">
        <h2 className="panel-title-mb">{t("userSettings.profile")}</h2>
        <div className="auth-form">
          <label className="field">
            {t("auth.email")}
            <input className="input" value={user?.email || ""} disabled style={{ opacity: 0.6 }} />
          </label>
          <label className="field">
            {t("userSettings.displayName")}
            <input
              className="input"
              value={values.display_name}
              onChange={(e) => setField("display_name", e.target.value)}
            />
            {errors.display_name && <span className="error-text">{errors.display_name}</span>}
          </label>
          <label className="field">
            {t("userSettings.phone")}
            <input
              className="input"
              value={values.phone ?? ""}
              onChange={(e) => setField("phone", e.target.value)}
              placeholder="010-0000-0000"
            />
          </label>
          {updateMut.isSuccess && <div className="banner banner-success">{t("userSettings.profileUpdated")}</div>}
          {updateMut.isError && <p className="error-text">{(updateMut.error as Error).message}</p>}
          <button className="btn btn-primary" onClick={() => updateMut.mutate()} disabled={updateMut.isPending}>
            {updateMut.isPending ? <span className="spinner" /> : t("common.save")}
          </button>
        </div>
      </div>

      <div className="panel">
        <h2 className="panel-title-mb">{t("userSettings.orgSection")}</h2>
        {user?.institutionName ? (
          <div className="stack-md">
            <div>
              <p className="detail-label">{t("userSettings.orgName")}</p>
              <p className="detail-value">{user.institutionName}</p>
            </div>
          </div>
        ) : (
          <p className="muted-text">{t("userSettings.noOrg")}</p>
        )}
      </div>
    </div>
  );
}
