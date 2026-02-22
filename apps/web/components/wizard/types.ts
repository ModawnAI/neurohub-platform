export interface WizardCaseInput {
  patient_ref: string;
  demographics: Record<string, string>;
}

export interface WizardDraft {
  [key: string]: unknown;
  service_id: string | null;
  pipeline_id: string | null;
  priority: number;
  cases: WizardCaseInput[];
  /** Per-case uploaded file IDs: caseIndex -> fileId[] */
  uploaded_files: Record<number, string[]>;
}

export const EMPTY_DRAFT: WizardDraft = {
  service_id: null,
  pipeline_id: null,
  priority: 5,
  cases: [{ patient_ref: "", demographics: {} }],
  uploaded_files: {},
};
