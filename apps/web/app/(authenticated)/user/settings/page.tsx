"use client";

import { useMutation } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { updateProfile } from "@/lib/api";
import { useZodForm } from "@/lib/use-zod-form";
import { profileUpdateSchema, type ProfileUpdateValues } from "@/lib/schemas";

export default function UserSettingsPage() {
  const { user, refreshUser } = useAuth();

  const { values, errors, setField, validate } = useZodForm<ProfileUpdateValues>(profileUpdateSchema, {
    display_name: user?.displayName || "",
    phone: "",
  });

  const updateMut = useMutation({
    mutationFn: () => {
      const data = validate();
      if (!data) throw new Error("입력값을 확인하세요");
      return updateProfile({ display_name: data.display_name, phone: data.phone || undefined });
    },
    onSuccess: () => {
      refreshUser();
    },
  });

  return (
    <div className="stack-lg">
      <h1 className="page-title">설정</h1>

      <div className="panel">
        <h2 className="panel-title-mb">프로필</h2>
        <div className="auth-form">
          <label className="field">
            이메일
            <input className="input" value={user?.email || ""} disabled style={{ opacity: 0.6 }} />
          </label>
          <label className="field">
            표시 이름
            <input
              className="input"
              value={values.display_name}
              onChange={(e) => setField("display_name", e.target.value)}
            />
            {errors.display_name && <span className="error-text">{errors.display_name}</span>}
          </label>
          <label className="field">
            연락처
            <input
              className="input"
              value={values.phone ?? ""}
              onChange={(e) => setField("phone", e.target.value)}
              placeholder="010-0000-0000"
            />
          </label>
          {updateMut.isSuccess && <div className="banner banner-success">프로필이 업데이트되었습니다.</div>}
          {updateMut.isError && <p className="error-text">{(updateMut.error as Error).message}</p>}
          <button className="btn btn-primary" onClick={() => updateMut.mutate()} disabled={updateMut.isPending}>
            {updateMut.isPending ? <span className="spinner" /> : "저장"}
          </button>
        </div>
      </div>

      <div className="panel">
        <h2 className="panel-title-mb">소속 기관</h2>
        {user?.institutionName ? (
          <div className="stack-md">
            <div>
              <p className="detail-label">기관명</p>
              <p className="detail-value">{user.institutionName}</p>
            </div>
          </div>
        ) : (
          <p className="muted-text">소속 기관이 없습니다.</p>
        )}
      </div>
    </div>
  );
}
