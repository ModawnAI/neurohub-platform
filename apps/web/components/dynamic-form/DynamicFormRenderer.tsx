"use client";

import { useCallback, useMemo } from "react";
import type { InputField, InputSchema } from "./types";

interface DynamicFormRendererProps {
  schema: InputSchema;
  values: Record<string, unknown>;
  onChange: (values: Record<string, unknown>) => void;
  errors?: Record<string, string>;
}

/**
 * Renders a form dynamically from a service's input_schema.
 * Supports text, number, select, date, radio, checkbox, textarea.
 * Handles conditional fields and validation rules.
 */
export function DynamicFormRenderer({
  schema,
  values,
  onChange,
  errors,
}: DynamicFormRendererProps) {
  const handleChange = useCallback(
    (key: string, value: unknown) => {
      onChange({ ...values, [key]: value });
    },
    [values, onChange],
  );

  const visibleFields = useMemo(() => {
    return schema.fields.filter((f) => {
      if (!f.condition) return true;
      return values[f.condition.field] === f.condition.value;
    });
  }, [schema.fields, values]);

  // Group fields
  const groups = useMemo(() => {
    const map = new Map<string, InputField[]>();
    for (const field of visibleFields) {
      const group = field.group ?? "__default__";
      const arr = map.get(group) ?? [];
      arr.push(field);
      map.set(group, arr);
    }
    return map;
  }, [visibleFields]);

  return (
    <div className="stack-md">
      {[...groups.entries()].map(([groupName, fields]) => (
        <fieldset key={groupName} className="stack-sm" style={{ border: "none", padding: 0 }}>
          {groupName !== "__default__" && (
            <legend
              style={{ fontWeight: 700, fontSize: 14, color: "var(--muted)", marginBottom: 8 }}
            >
              {groupName}
            </legend>
          )}
          {fields.map((field) => (
            <DynamicField
              key={field.key}
              field={field}
              value={values[field.key]}
              error={errors?.[field.key]}
              onChange={(v) => handleChange(field.key, v)}
            />
          ))}
        </fieldset>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Validation helper
// ---------------------------------------------------------------------------

export function validateDynamicForm(
  schema: InputSchema,
  values: Record<string, unknown>,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of schema.fields) {
    // Skip hidden conditional fields
    if (field.condition && values[field.condition.field] !== field.condition.value) continue;

    const val = values[field.key];
    if (field.required && (val === undefined || val === null || val === "")) {
      errors[field.key] = `${field.label}은(는) 필수 항목입니다`;
      continue;
    }
    if (val === undefined || val === null || val === "") continue;

    const v = field.validation;
    if (!v) continue;

    if (typeof val === "number") {
      if (v.min !== undefined && val < v.min) errors[field.key] = `최솟값: ${v.min}`;
      if (v.max !== undefined && val > v.max) errors[field.key] = `최댓값: ${v.max}`;
    }
    if (typeof val === "string") {
      if (v.min_length !== undefined && val.length < v.min_length)
        errors[field.key] = `최소 ${v.min_length}자`;
      if (v.max_length !== undefined && val.length > v.max_length)
        errors[field.key] = `최대 ${v.max_length}자`;
      if (v.pattern && !new RegExp(v.pattern).test(val))
        errors[field.key] = "형식이 올바르지 않습니다";
    }
  }
  return errors;
}

// ---------------------------------------------------------------------------
// Individual field renderer
// ---------------------------------------------------------------------------

interface DynamicFieldProps {
  field: InputField;
  value: unknown;
  error?: string;
  onChange: (value: unknown) => void;
}

function DynamicField({ field, value, error, onChange }: DynamicFieldProps) {
  const id = `field-${field.key}`;
  const baseStyle = { width: "100%" };

  const label = (
    <label
      htmlFor={id}
      style={{ fontWeight: 600, fontSize: 13, display: "block", marginBottom: 4 }}
    >
      {field.label}
      {field.required && <span style={{ color: "var(--danger)" }}> *</span>}
    </label>
  );

  const helpText = field.help_text && (
    <span style={{ fontSize: 12, color: "var(--muted)" }}>{field.help_text}</span>
  );

  const errorEl = error && <span style={{ fontSize: 12, color: "var(--danger)" }}>{error}</span>;

  let input: React.ReactNode;

  switch (field.type) {
    case "text":
    case "date":
      input = (
        <input
          id={id}
          className="input"
          type={field.type}
          placeholder={field.placeholder}
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
          style={baseStyle}
        />
      );
      break;

    case "number":
      input = (
        <input
          id={id}
          className="input"
          type="number"
          placeholder={field.placeholder}
          value={value !== undefined && value !== null ? String(value) : ""}
          min={field.validation?.min}
          max={field.validation?.max}
          onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
          style={baseStyle}
        />
      );
      break;

    case "select":
      input = (
        <select
          id={id}
          className="input"
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
          style={baseStyle}
        >
          <option value="">{field.placeholder ?? "선택하세요"}</option>
          {field.options?.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      );
      break;

    case "radio":
      input = (
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          {field.options?.map((opt) => (
            <label
              key={opt.value}
              style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13 }}
            >
              <input
                type="radio"
                name={field.key}
                value={opt.value}
                checked={value === opt.value}
                onChange={() => onChange(opt.value)}
              />
              {opt.label}
            </label>
          ))}
        </div>
      );
      break;

    case "checkbox":
      input = (
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
          <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} />
          {field.placeholder ?? field.label}
        </label>
      );
      break;

    case "textarea":
      input = (
        <textarea
          id={id}
          className="input"
          placeholder={field.placeholder}
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          style={baseStyle}
        />
      );
      break;

    default:
      input = (
        <input
          id={id}
          className="input"
          type="text"
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
          style={baseStyle}
        />
      );
  }

  return (
    <div style={{ marginBottom: 12 }}>
      {field.type !== "checkbox" && label}
      {input}
      {helpText}
      {errorEl}
    </div>
  );
}
