import { supabase } from "@/lib/supabase";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api/v1";

export type RequestStatus =
  | "CREATED"
  | "RECEIVING"
  | "STAGING"
  | "READY_TO_COMPUTE"
  | "COMPUTING"
  | "QC"
  | "REPORTING"
  | "EXPERT_REVIEW"
  | "FINAL"
  | "FAILED"
  | "CANCELLED";

export interface RequestRead {
  id: string;
  institution_id: string;
  service_id: string;
  pipeline_id: string;
  status: RequestStatus;
  priority: number;
  case_count: number;
  created_at: string;
  updated_at: string | null;
  cancel_reason: string | null;
}

export interface ServiceRead {
  id: string;
  institution_id: string;
  name: string;
  display_name: string;
  version: string;
  status: string;
  department: string | null;
  created_at: string;
}

export interface PipelineRead {
  id: string;
  service_id: string;
  name: string;
  version: string;
  is_default: boolean;
  created_at: string;
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  if (typeof window !== "undefined" && supabase) {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (session?.access_token) {
      return {
        Authorization: `Bearer ${session.access_token}`,
      };
    }
  }

  // Local fallback headers for fast development bootstrap.
  return {
    "X-User-Id": process.env.NEXT_PUBLIC_DEV_USER_ID ?? "11111111-1111-1111-1111-111111111111",
    "X-Username": process.env.NEXT_PUBLIC_DEV_USERNAME ?? "dev-user",
    "X-Institution-Id":
      process.env.NEXT_PUBLIC_DEV_INSTITUTION_ID ?? "00000000-0000-0000-0000-000000000001",
    "X-Roles": process.env.NEXT_PUBLIC_DEV_ROLES ?? "SYSTEM_ADMIN",
  };
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = "";
    try {
      const body = (await response.json()) as { detail?: string | { message?: string } };
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (body.detail?.message) {
        detail = body.detail.message;
      }
    } catch {
      detail = "";
    }

    const message = detail || `API ${response.status}: ${response.statusText}`;
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function listRequests() {
  return apiFetch<{ items: RequestRead[]; total: number }>("/requests");
}

export async function getRequest(requestId: string) {
  return apiFetch<RequestRead>(`/requests/${requestId}`);
}

export async function createRequest(payload: {
  service_id: string;
  pipeline_id: string;
  priority: number;
  cases: Array<{ patient_ref: string; demographics?: Record<string, unknown> }>;
  idempotency_key?: string;
}) {
  return apiFetch<RequestRead>("/requests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function transitionRequest(requestId: string, targetStatus: RequestStatus, note?: string) {
  return apiFetch<RequestRead>(`/requests/${requestId}/transition`, {
    method: "POST",
    body: JSON.stringify({ target_status: targetStatus, note }),
  });
}

export async function confirmRequest(requestId: string) {
  return apiFetch<RequestRead>(`/requests/${requestId}/confirm`, {
    method: "POST",
    body: JSON.stringify({ confirm_note: "웹에서 확인 완료" }),
  });
}

export async function submitRequest(requestId: string) {
  return apiFetch<{ request_id: string; status: RequestStatus; run_ids: string[] }>(
    `/requests/${requestId}/submit`,
    {
      method: "POST",
    },
  );
}

export async function advanceRequest(requestId: string, targetStatus: string, note?: string) {
  return apiFetch<RequestRead>(`/requests/${requestId}/transition`, {
    method: "POST",
    body: JSON.stringify({ target_status: targetStatus, note }),
  });
}

export async function cancelRequest(requestId: string, reason: string) {
  return apiFetch<RequestRead>(`/requests/${requestId}/cancel`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function listServices() {
  return apiFetch<{ items: ServiceRead[] }>("/services");
}

export async function listPipelines(serviceId: string) {
  return apiFetch<{ items: PipelineRead[] }>(`/services/${serviceId}/pipelines`);
}

// ── Auth / Onboarding ──

export interface OnboardingPayload {
  user_type: "SERVICE_USER" | "EXPERT" | "ADMIN";
  display_name: string;
  phone?: string;
  specialization?: string;
  bio?: string;
  organization_name?: string;
  organization_code?: string;
  organization_type?: "individual" | "hospital" | "clinic";
}

export interface MeResponse {
  id: string;
  username: string;
  display_name: string | null;
  email: string | null;
  phone: string | null;
  user_type: string | null;
  institution_id: string | null;
  institution_name: string | null;
  roles: string[];
  expert_status: string | null;
  specialization: string | null;
  bio: string | null;
  onboarding_completed: boolean;
  created_at: string | null;
}

export async function completeOnboarding(payload: OnboardingPayload) {
  return apiFetch<MeResponse>("/auth/onboarding", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getMe() {
  return apiFetch<MeResponse>("/auth/me");
}

export async function updateProfile(payload: Partial<{ display_name: string; phone: string; specialization: string; bio: string }>) {
  return apiFetch<MeResponse>("/auth/me", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

// ── Reviews (Expert) ──

export interface ReviewQueueItem {
  id: string;
  service_name: string | null;
  service_display_name: string | null;
  status: string;
  case_count: number;
  priority: number;
  requested_by: string | null;
  institution_id: string;
  created_at: string;
  updated_at: string | null;
}

export async function listReviewQueue(status?: string) {
  const params = status ? `?status=${status}` : "";
  return apiFetch<{ items: ReviewQueueItem[]; total: number }>(`/reviews/queue${params}`);
}

export async function getReviewDetail(requestId: string) {
  return apiFetch<{
    request: RequestRead;
    cases: Array<Record<string, unknown>>;
    runs: Array<Record<string, unknown>>;
    reports: Array<Record<string, unknown>>;
    qc_decisions: Array<Record<string, unknown>>;
    report_reviews: Array<Record<string, unknown>>;
  }>(`/reviews/${requestId}`);
}

export async function submitQCDecision(requestId: string, payload: { decision: string; qc_score?: number; comments?: string }) {
  return apiFetch<{ status: string; decision: string }>(`/reviews/${requestId}/qc-decision`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function submitReportReview(requestId: string, payload: { decision: string; comments?: string }) {
  return apiFetch<{ status: string; decision: string }>(`/reviews/${requestId}/report-review`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ── Users (Admin) ──

export interface UserRead {
  id: string;
  username: string;
  display_name: string | null;
  email: string | null;
  phone: string | null;
  user_type: string | null;
  is_active: boolean;
  institution_id: string | null;
  institution_name: string | null;
  role_scope: string | null;
  expert_status: string | null;
  specialization: string | null;
  onboarding_completed: boolean;
  created_at: string | null;
  last_login_at: string | null;
}

export async function listUsers(params?: { user_type?: string; expert_status?: string }) {
  const searchParams = new URLSearchParams();
  if (params?.user_type) searchParams.set("user_type", params.user_type);
  if (params?.expert_status) searchParams.set("expert_status", params.expert_status);
  const qs = searchParams.toString();
  return apiFetch<{ items: UserRead[]; total: number }>(`/users${qs ? `?${qs}` : ""}`);
}

export async function getUser(userId: string) {
  return apiFetch<UserRead>(`/users/${userId}`);
}

export async function approveExpert(userId: string) {
  return apiFetch<UserRead>(`/users/${userId}/approve-expert`, { method: "POST" });
}

export async function rejectExpert(userId: string, reason?: string) {
  return apiFetch<UserRead>(`/users/${userId}/reject-expert`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

// ── Organizations ──

export interface OrgRead {
  id: string;
  code: string;
  name: string;
  status: string;
  institution_type: string;
  contact_email: string | null;
  contact_phone: string | null;
  member_count: number;
  created_at: string | null;
}

export interface MemberRead {
  user_id: string;
  username: string | null;
  display_name: string | null;
  email: string | null;
  role_scope: string | null;
  user_type: string | null;
  created_at: string | null;
}

export async function createOrganization(payload: { name: string; code?: string; institution_type?: string; contact_email?: string; contact_phone?: string }) {
  return apiFetch<OrgRead>("/organizations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listOrganizations() {
  return apiFetch<{ items: OrgRead[]; total: number }>("/organizations");
}

export async function listOrgMembers(orgId: string) {
  return apiFetch<MemberRead[]>(`/organizations/${orgId}/members`);
}

export async function inviteMember(orgId: string, email: string, roleScope?: string) {
  return apiFetch<{ id: string; invite_token: string }>(`/organizations/${orgId}/invite`, {
    method: "POST",
    body: JSON.stringify({ email, role_scope: roleScope }),
  });
}

export async function joinOrganization(token: string) {
  return apiFetch<{ status: string; institution_id: string }>("/organizations/join", {
    method: "POST",
    body: JSON.stringify({ invite_token: token }),
  });
}

// ── Admin ──

export interface AdminStats {
  total_requests: number;
  status_counts: Record<string, number>;
  active_users: number;
  pending_experts: number;
  approved_experts: number;
  total_services: number;
  total_organizations: number;
}

export async function getAdminStats() {
  return apiFetch<AdminStats>("/admin/stats");
}

export async function listAllRequests(status?: string) {
  const params = status ? `?status=${status}` : "";
  return apiFetch<{ items: RequestRead[]; total: number }>(`/admin/requests${params}`);
}
