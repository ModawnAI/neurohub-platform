/** Types matching the backend ServiceDefinition JSON schemas. */

export interface InputFieldCondition {
  field: string;
  value: string | number | boolean;
}

export interface InputFieldValidation {
  min?: number;
  max?: number;
  min_length?: number;
  max_length?: number;
  pattern?: string;
}

export interface InputField {
  key: string;
  type: "text" | "number" | "select" | "date" | "radio" | "checkbox" | "textarea";
  label: string;
  label_en?: string;
  placeholder?: string;
  required?: boolean;
  default?: unknown;
  options?: { value: string; label: string }[];
  validation?: InputFieldValidation;
  condition?: InputFieldCondition;
  help_text?: string;
  group?: string;
}

export interface InputSchema {
  fields: InputField[];
}

export interface UploadSlot {
  key: string;
  label: string;
  label_en?: string;
  required?: boolean;
  accepted_types?: string[];
  accepted_extensions?: string[];
  min_files?: number;
  max_files?: number;
  description?: string;
  help_text?: string;
}

export interface OptionField {
  key: string;
  type: "select" | "number" | "checkbox" | "text" | "radio";
  label: string;
  label_en?: string;
  required?: boolean;
  default?: unknown;
  options?: { value: string; label: string }[];
  validation?: InputFieldValidation;
  help_text?: string;
}

export interface OptionsSchema {
  fields: OptionField[];
}

export interface ServiceDefinition {
  id: string;
  name: string;
  display_name: string;
  input_schema?: InputSchema | null;
  upload_slots?: UploadSlot[] | null;
  options_schema?: OptionsSchema | null;
  pricing?: {
    base_price: number;
    per_case_price: number;
    currency: string;
    volume_discounts: { min_cases: number; discount_percent: number }[];
  } | null;
  output_schema?: { fields: { key: string; type: string; label: string }[] } | null;
}
