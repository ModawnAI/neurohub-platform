"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiFetch, API_BASE } from "@/lib/api";

export interface AuthUser {
  id: string;
  email: string | null;
  userType: "SERVICE_USER" | "EXPERT" | "ADMIN" | null;
  displayName: string | null;
  institutionId: string | null;
  institutionName: string | null;
  roles: string[];
  expertStatus: string | null;
  specialization: string | null;
  onboardingCompleted: boolean;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, name?: string) => Promise<{ userId: string }>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<AuthUser | null>;
}

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  signIn: async () => {},
  signUp: async (_e, _p, _n?) => ({ userId: "" }),
  signOut: async () => {},
  refreshUser: async () => null,
});

export function useAuth() {
  return useContext(AuthContext);
}

interface MeResponse {
  id: string;
  username: string;
  display_name: string | null;
  email: string | null;
  user_type: string | null;
  institution_id: string | null;
  institution_name: string | null;
  roles: string[];
  expert_status: string | null;
  specialization: string | null;
  onboarding_completed: boolean;
}

function getStoredToken(): string | null {
  return typeof window !== "undefined" ? localStorage.getItem("nh-token") : null;
}

function setStoredToken(token: string) {
  localStorage.setItem("nh-token", token);
}

function clearStoredToken() {
  localStorage.removeItem("nh-token");
}

function clearCookies() {
  document.cookie = "nh-user-type=; path=/; max-age=0";
  document.cookie = "nh-onboarded=; path=/; max-age=0";
  document.cookie = "nh-expert-status=; path=/; max-age=0";
}

export function useAuthProvider(): AuthContextValue {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async (): Promise<AuthUser | null> => {
    try {
      const me = await apiFetch<MeResponse>("/auth/me");
      const authUser: AuthUser = {
        id: me.id,
        email: me.email,
        userType: me.user_type as AuthUser["userType"],
        displayName: me.display_name,
        institutionId: me.institution_id,
        institutionName: me.institution_name,
        roles: me.roles,
        expertStatus: me.expert_status,
        specialization: me.specialization ?? null,
        onboardingCompleted: me.onboarding_completed,
      };
      document.cookie = `nh-user-type=${me.user_type || ""}; path=/; max-age=86400; SameSite=Lax`;
      document.cookie = `nh-onboarded=${me.onboarding_completed ? "1" : "0"}; path=/; max-age=86400; SameSite=Lax`;
      document.cookie = `nh-expert-status=${me.expert_status || ""}; path=/; max-age=86400; SameSite=Lax`;
      return authUser;
    } catch {
      return null;
    }
  }, []);

  const refreshUser = useCallback(async () => {
    const authUser = await fetchMe();
    setUser(authUser);
    return authUser;
  }, [fetchMe]);

  useEffect(() => {
    const token = getStoredToken();
    if (token) {
      fetchMe().then((u) => {
        if (!u) {
          // Token is invalid/expired — clear it
          clearStoredToken();
          clearCookies();
        }
        setUser(u);
        setLoading(false);
      });
    } else {
      // No token — check if dev fallback headers are set
      const devUserId = process.env.NEXT_PUBLIC_DEV_USER_ID;
      if (devUserId) {
        fetchMe().then((u) => {
          setUser(u);
          setLoading(false);
        });
      } else {
        setUser(null);
        setLoading(false);
      }
    }
  }, [fetchMe]);

  const signIn = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "로그인 실패" }));
      throw new Error(err.detail || "로그인 실패");
    }
    const data = await res.json();
    setStoredToken(data.access_token);
    const authUser = await fetchMe();
    setUser(authUser);
  }, [fetchMe]);

  const signUp = useCallback(async (email: string, password: string, name?: string) => {
    const res = await fetch(`${API_BASE}/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, ...(name ? { name } : {}) }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg =
        (typeof err.detail === "string" && err.detail) ||
        (typeof err.message === "string" && err.message) ||
        "회원가입 실패";
      // 409 = email already exists → try logging in instead
      if (res.status === 409) {
        throw new Error("이미 등록된 이메일입니다. 로그인 페이지에서 로그인해 주세요.");
      }
      throw new Error(msg);
    }
    const data = await res.json();
    setStoredToken(data.access_token);
    return { userId: "" };
  }, []);

  const signOut = useCallback(async () => {
    clearStoredToken();
    clearCookies();
    setUser(null);
    window.location.href = "/login";
  }, []);

  return { user, loading, signIn, signUp, signOut, refreshUser };
}

export function getRoleHomePath(userType: string | null | undefined): string {
  switch (userType) {
    case "SERVICE_USER":
      return "/user/dashboard";
    case "EXPERT":
      return "/expert/dashboard";
    case "ADMIN":
      return "/admin/dashboard";
    default:
      return "/onboarding";
  }
}
