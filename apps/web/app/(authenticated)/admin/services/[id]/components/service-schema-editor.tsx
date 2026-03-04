"use client";

import { useState } from "react";
import { CaretDown, FileText, UploadSimple, Sliders, Package } from "phosphor-react";
import type { ServiceRead } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

import { ServiceInputSchema } from "./service-input-schema";
import { ServiceUploadSlots } from "./service-upload-slots";
import { ServiceOptionsSchema } from "./service-options-schema";
import { ServiceOutputSchema } from "./service-output-schema";

interface Section {
  id: string;
  labelKo: string;
  labelEn: string;
  icon: React.ReactNode;
  count: number;
  component: React.ReactNode;
}

export function ServiceSchemaEditor({ service }: { service: ServiceRead }) {
  const { locale } = useTranslation();
  const ko = locale === "ko";

  const hasInput = (service.input_schema as Record<string, unknown[]> | null)?.fields?.length ?? 0;
  const hasUpload = service.upload_slots?.length ?? 0;
  const hasOptions = (service.options_schema as Record<string, unknown[]> | null)?.fields?.length ?? 0;
  const hasOutput = service.output_schema?.fields?.length ?? 0;

  const sections: Section[] = [
    { id: "input", labelKo: "입력 필드", labelEn: "Input Fields", icon: <FileText size={16} />, count: hasInput, component: <ServiceInputSchema service={service} /> },
    { id: "upload", labelKo: "업로드 슬롯", labelEn: "Upload Slots", icon: <UploadSimple size={16} />, count: hasUpload, component: <ServiceUploadSlots service={service} /> },
    { id: "options", labelKo: "분석 옵션", labelEn: "Analysis Options", icon: <Sliders size={16} />, count: hasOptions, component: <ServiceOptionsSchema service={service} /> },
    { id: "output", labelKo: "출력 스키마", labelEn: "Output Schema", icon: <Package size={16} />, count: hasOutput, component: <ServiceOutputSchema service={service} /> },
  ];

  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const toggle = (id: string) => setCollapsed((prev) => ({ ...prev, [id]: !prev[id] }));

  return (
    <div className="stack-md">
      {sections.map((section) => (
        <div key={section.id} className="panel" style={{ padding: 0, overflow: "hidden" }}>
          <button
            type="button"
            className="panel-collapse-header"
            onClick={() => toggle(section.id)}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ color: "var(--primary)" }}>{section.icon}</span>
              <span style={{ fontWeight: 600, fontSize: 14 }}>
                {ko ? section.labelKo : section.labelEn}
              </span>
              {section.count > 0 && (
                <span className="status-chip status-final" style={{ fontSize: 10, padding: "1px 6px" }}>
                  {section.count}
                </span>
              )}
            </div>
            <CaretDown
              size={16}
              className={`chevron-toggle ${collapsed[section.id] ? "collapsed" : ""}`}
            />
          </button>
          {!collapsed[section.id] && (
            <div style={{ padding: "0 18px 18px" }}>
              {section.component}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
