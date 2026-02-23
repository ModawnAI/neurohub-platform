import { type Locale, t as translate } from "@/lib/i18n";
import { supabase } from "@/lib/supabase";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api/v1";

function getLocale(): Locale {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("neurohub-locale");
    if (stored === "ko" || stored === "en") return stored;
  }
  return "ko";
}

// ── Typed API Error ──

export class ApiError extends Error {
  status: number;
  code: string;
  detail: string;

  constructor(status: number, code: string, message: string, detail = "") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

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
  description: string | null;
  version: number;
  version_label: string;
  status: string;
  department: string | null;
  category: string | null;
  input_schema: import("@/components/dynamic-form/types").InputSchema | null;
  upload_slots: import("@/components/dynamic-form/types").UploadSlot[] | null;
  options_schema: import("@/components/dynamic-form/types").OptionsSchema | null;
  pricing: {
    base_price: number;
    per_case_price: number;
    currency: string;
    volume_discounts: { min_cases: number; discount_percent: number }[];
  } | null;
  output_schema: { fields: { key: string; type: string; label: string }[] } | null;
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
    let errorCode = "";
    try {
      const body = (await response.json()) as {
        detail?: string | { error?: string; message?: string };
      };
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (body.detail) {
        errorCode = body.detail.error ?? "";
        detail = body.detail.message ?? "";
      }
    } catch {
      detail = "";
    }

    const locale = getLocale();
    if (response.status === 409 && errorCode === "IDEMPOTENCY_CONFLICT") {
      throw new ApiError(
        409,
        "IDEMPOTENCY_CONFLICT",
        translate("apiError.idempotencyConflict", locale),
        detail,
      );
    }
    if (response.status === 409) {
      throw new ApiError(
        409,
        "CONFLICT",
        detail || translate("apiError.statusConflict", locale),
        detail,
      );
    }
    if (response.status === 401) {
      if (typeof window !== "undefined") window.location.href = "/login";
      throw new ApiError(401, "UNAUTHORIZED", translate("apiError.unauthorized", locale), detail);
    }
    if (response.status === 403) {
      throw new ApiError(403, "FORBIDDEN", translate("apiError.forbidden", locale), detail);
    }

    const message = detail || `API ${response.status}: ${response.statusText}`;
    throw new ApiError(response.status, errorCode || `HTTP_${response.status}`, message, detail);
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

export async function transitionRequest(
  requestId: string,
  targetStatus: RequestStatus,
  note?: string,
) {
  return apiFetch<RequestRead>(`/requests/${requestId}/transition`, {
    method: "POST",
    body: JSON.stringify({ target_status: targetStatus, note }),
  });
}

export async function confirmRequest(requestId: string) {
  return apiFetch<RequestRead>(`/requests/${requestId}/confirm`, {
    method: "POST",
    body: JSON.stringify({ confirm_note: translate("apiError.confirmedFromWeb", getLocale()) }),
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

export async function updateProfile(
  payload: Partial<{ display_name: string; phone: string; specialization: string; bio: string }>,
) {
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

export async function submitQCDecision(
  requestId: string,
  payload: { decision: string; qc_score?: number; comments?: string },
) {
  return apiFetch<{ status: string; decision: string }>(`/reviews/${requestId}/qc-decision`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function submitReportReview(
  requestId: string,
  payload: { decision: string; comments?: string },
) {
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

export async function createOrganization(payload: {
  name: string;
  code?: string;
  institution_type?: string;
  contact_email?: string;
  contact_phone?: string;
}) {
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

// ── File Upload ──

export interface CaseFileRead {
  id: string;
  case_id: string;
  slot: string;
  filename: string;
  content_type: string;
  size_bytes: number | null;
  checksum: string | null;
  status: string;
  created_at: string;
}

export interface CaseRead {
  id: string;
  request_id: string;
  patient_ref: string;
  status: string;
  demographics: Record<string, unknown> | null;
}

export async function listCases(requestId: string) {
  return apiFetch<{ items: CaseRead[] }>(`/requests/${requestId}/cases`);
}

export async function initiateUpload(
  requestId: string,
  caseId: string,
  payload: { filename: string; content_type: string; slot: string },
) {
  return apiFetch<{ file_id: string; upload_url: string; upload_session_id: string }>(
    `/requests/${requestId}/cases/${caseId}/files/presign`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export async function completeUpload(
  requestId: string,
  caseId: string,
  fileId: string,
  payload: { checksum: string; size_bytes: number },
) {
  return apiFetch<CaseFileRead>(`/requests/${requestId}/cases/${caseId}/files/${fileId}/complete`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function uploadFileToStorage(
  url: string,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
      };
    }
    xhr.onload = () =>
      xhr.status >= 200 && xhr.status < 300
        ? resolve()
        : reject(new Error(`Upload failed: ${xhr.status}`));
    xhr.onerror = () => reject(new Error("Upload network error"));
    xhr.send(file);
  });
}

export async function listCaseFiles(requestId: string, caseId: string) {
  return apiFetch<{ items: CaseFileRead[] }>(`/requests/${requestId}/cases/${caseId}/files`);
}

export async function getDownloadUrl(requestId: string, caseId: string, fileId: string) {
  return apiFetch<{ download_url: string; expires_in: number }>(
    `/requests/${requestId}/cases/${caseId}/files/${fileId}/download`,
  );
}

// ── Notifications ──

export interface NotificationRead {
  id: string;
  event_type: string;
  title: string;
  body: string | null;
  entity_type: string | null;
  entity_id: string | null;
  is_read: boolean;
  created_at: string;
}

export async function listNotifications(unreadOnly = false) {
  const params = unreadOnly ? "?unread_only=true" : "";
  return apiFetch<{ items: NotificationRead[]; total: number }>(`/notifications${params}`);
}

export async function markNotificationRead(notificationId: string) {
  return apiFetch<{ status: string }>(`/notifications/${notificationId}/read`, { method: "POST" });
}

export async function markAllNotificationsRead() {
  return apiFetch<{ updated: number }>("/notifications/read-all", { method: "POST" });
}

// ── API Keys (Admin) ──

export interface ApiKeyRead {
  id: string;
  name: string;
  key_prefix: string;
  status: string;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
}

export async function listApiKeys(orgId: string) {
  return apiFetch<{ items: ApiKeyRead[] }>(`/organizations/${orgId}/api-keys`);
}

export async function createApiKey(
  orgId: string,
  payload: { name: string; expires_in_days?: number },
) {
  return apiFetch<{
    id: string;
    api_key: string;
    name: string;
    key_prefix: string;
    expires_at: string | null;
  }>(`/organizations/${orgId}/api-keys`, { method: "POST", body: JSON.stringify(payload) });
}

export async function revokeApiKey(orgId: string, keyId: string) {
  return apiFetch<{ status: string }>(`/organizations/${orgId}/api-keys/${keyId}`, {
    method: "DELETE",
  });
}

// ── Billing ──

export interface UsageEntry {
  service_name: string;
  charge_type: string;
  total_amount: number;
  count: number;
}

export async function getUsage(startDate: string, endDate: string) {
  return apiFetch<{ items: UsageEntry[] }>(
    `/billing/usage?start_date=${startDate}&end_date=${endDate}`,
  );
}

// ── Admin: Audit Logs ──

export interface AuditLogRead {
  id: string;
  actor_id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  diff: Record<string, unknown> | null;
  created_at: string;
}

export async function listAuditLogs(params?: {
  action?: string;
  entity_type?: string;
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.action) searchParams.set("action", params.action);
  if (params?.entity_type) searchParams.set("entity_type", params.entity_type);
  if (params?.from) searchParams.set("from", params.from);
  if (params?.to) searchParams.set("to", params.to);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiFetch<{ items: AuditLogRead[]; total: number }>(
    `/admin/audit-logs${qs ? `?${qs}` : ""}`,
  );
}

// ── Admin: Service CRUD ──

export async function createService(payload: {
  name: string;
  display_name: string;
  version?: string;
  department?: string;
  description?: string;
}) {
  return apiFetch<ServiceRead>("/services", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateService(
  serviceId: string,
  payload: {
    display_name?: string;
    version?: string;
    department?: string;
    description?: string;
    status?: string;
  },
) {
  return apiFetch<ServiceRead>(`/services/${serviceId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

// ── Admin: Organization Update ──

export async function updateOrganization(
  orgId: string,
  payload: { name?: string; contact_email?: string; contact_phone?: string; status?: string },
) {
  return apiFetch<OrgRead>(`/organizations/${orgId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

// ── Transition Record (for enhanced timeline) ──

export interface TransitionRecord {
  from_status: string;
  to_status: string;
  actor_id: string | null;
  note: string | null;
  created_at: string;
}
