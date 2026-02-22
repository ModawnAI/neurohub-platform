"use client";

import { MagnifyingGlass, Plus, FolderOpen, Bell, FileText } from "phosphor-react";
import { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

const PRESET_ICONS: Record<string, ReactNode> = {
  search: <MagnifyingGlass size={48} weight="light" />,
  create: <Plus size={48} weight="light" />,
  folder: <FolderOpen size={48} weight="light" />,
  notification: <Bell size={48} weight="light" />,
  document: <FileText size={48} weight="light" />,
};

export function EmptyState({ icon, title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="empty-state" role="status">
      <div className="empty-state-icon">
        {icon || PRESET_ICONS.folder}
      </div>
      <h3 className="empty-state-title">{title}</h3>
      {description && <p className="empty-state-description">{description}</p>}
      {actionLabel && onAction && (
        <button className="btn btn-primary" onClick={onAction} type="button">
          {actionLabel}
        </button>
      )}
    </div>
  );
}
