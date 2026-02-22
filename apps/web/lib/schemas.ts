import { z } from "zod";

// ── Onboarding ──

export const onboardingSchema = z
  .object({
    user_type: z.enum(["SERVICE_USER", "EXPERT", "ADMIN"], {
      required_error: "사용자 유형을 선택하세요",
    }),
    display_name: z.string().min(1, "표시 이름을 입력하세요").max(100, "100자 이하로 입력하세요"),
    phone: z.string().max(20).optional(),
    specialization: z.string().max(200).optional(),
    bio: z.string().max(1000).optional(),
    organization_name: z.string().max(200).optional(),
    organization_code: z.string().max(50).optional(),
    organization_type: z.enum(["individual", "hospital", "clinic"]).optional(),
  })
  .superRefine((data, ctx) => {
    if (data.user_type === "ADMIN" && !data.organization_name?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "관리자는 기관명을 입력해야 합니다",
        path: ["organization_name"],
      });
    }
    if (
      data.user_type === "SERVICE_USER" &&
      data.organization_type === "hospital" &&
      !data.organization_name?.trim()
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "기관명을 입력하세요",
        path: ["organization_name"],
      });
    }
  });

export type OnboardingFormValues = z.infer<typeof onboardingSchema>;

// ── Profile Update ──

export const profileUpdateSchema = z.object({
  display_name: z.string().min(1, "표시 이름을 입력하세요").max(100, "100자 이하로 입력하세요"),
  phone: z.string().max(20).optional(),
  specialization: z.string().max(200).optional(),
  bio: z.string().max(1000).optional(),
});

export type ProfileUpdateValues = z.infer<typeof profileUpdateSchema>;

// ── New Request ──

export const caseInputSchema = z.object({
  patient_ref: z.string().min(1, "환자 참조 ID를 입력하세요"),
  demographics: z.record(z.string()).optional(),
});

export const newRequestSchema = z.object({
  service_id: z.string().uuid("서비스를 선택하세요"),
  pipeline_id: z.string().uuid("파이프라인이 필요합니다"),
  priority: z.number().int().min(1).max(10).default(5),
  cases: z.array(caseInputSchema).min(1, "최소 1개의 케이스가 필요합니다"),
});

export type NewRequestValues = z.infer<typeof newRequestSchema>;

// ── File Upload ──

export const fileUploadSchema = z.object({
  filename: z.string().min(1),
  content_type: z.string().min(1),
  slot: z.string().min(1, "파일 슬롯을 선택하세요"),
});

export type FileUploadValues = z.infer<typeof fileUploadSchema>;

// ── QC Decision ──

export const qcDecisionSchema = z.object({
  decision: z.enum(["APPROVE", "REJECT", "RERUN"], {
    required_error: "결정을 선택하세요",
  }),
  qc_score: z.number().min(0).max(100).optional(),
  comments: z.string().max(2000).optional(),
});

export type QCDecisionValues = z.infer<typeof qcDecisionSchema>;

// ── Report Review ──

export const reportReviewSchema = z.object({
  decision: z.enum(["APPROVE", "REVISION_NEEDED"], {
    required_error: "결정을 선택하세요",
  }),
  comments: z.string().max(2000).optional(),
});

export type ReportReviewValues = z.infer<typeof reportReviewSchema>;

// ── Service Create (Admin) ──

export const serviceCreateSchema = z.object({
  name: z
    .string()
    .min(1, "서비스 이름을 입력하세요")
    .max(100)
    .regex(/^[a-z0-9_-]+$/, "영문 소문자, 숫자, 하이픈, 언더스코어만 사용 가능"),
  display_name: z.string().min(1, "표시 이름을 입력하세요").max(200),
  version: z.string().default("1.0"),
  department: z.string().max(100).optional(),
  description: z.string().max(2000).optional(),
});

export type ServiceCreateValues = z.infer<typeof serviceCreateSchema>;

// ── Service Update (Admin) ──

export const serviceUpdateSchema = z.object({
  display_name: z.string().min(1).max(200).optional(),
  version: z.string().optional(),
  department: z.string().max(100).optional(),
  description: z.string().max(2000).optional(),
  status: z.enum(["ACTIVE", "INACTIVE"]).optional(),
});

export type ServiceUpdateValues = z.infer<typeof serviceUpdateSchema>;
