"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";

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
  signUp: (email: string, password: string) => Promise<{ userId: string }>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  signIn: async () => {},
  signUp: async () => ({ userId: "" }),
  signOut: async () => {},
  refreshUser: async () => {},
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
  }, [fetchMe]);

  useEffect(() => {
    if (!supabase) {
      // Dev mode — fetch me with dev headers
      fetchMe().then((u) => {
        setUser(u);
        setLoading(false);
      });
      return;
    }

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, session) => {
      if (session) {
        const authUser = await fetchMe();
        setUser(authUser);
      } else {
        setUser(null);
        document.cookie = "nh-user-type=; path=/; max-age=0";
        document.cookie = "nh-onboarded=; path=/; max-age=0";
        document.cookie = "nh-expert-status=; path=/; max-age=0";
      }
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, [fetchMe]);

  const signIn = useCallback(async (email: string, password: string) => {
    if (!supabase) throw new Error("Supabase not configured");
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    if (!supabase) throw new Error("Supabase not configured");
    const { data, error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
    return { userId: data.user?.id ?? "" };
  }, []);

  const signOut = useCallback(async () => {
    if (supabase) {
      await supabase.auth.signOut();
    }
    setUser(null);
    document.cookie = "nh-user-type=; path=/; max-age=0";
    document.cookie = "nh-onboarded=; path=/; max-age=0";
    document.cookie = "nh-expert-status=; path=/; max-age=0";
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
