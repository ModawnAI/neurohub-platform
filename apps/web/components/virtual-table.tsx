"use client";

import { useRef, ReactNode } from "react";

interface VirtualTableProps<T> {
  data: T[];
  columns: {
    key: string;
    header: string;
    render: (item: T) => ReactNode;
    hideOnMobile?: boolean;
  }[];
  rowHeight?: number;
  maxHeight?: number;
  emptyMessage?: string;
}

export function VirtualTable<T extends { id?: string }>({
  data,
  columns,
  rowHeight = 48,
  maxHeight = 600,
  emptyMessage = "데이터가 없습니다",
}: VirtualTableProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);

  if (data.length === 0) {
    return (
      <div className="empty-state">
        <p className="empty-state-title">{emptyMessage}</p>
      </div>
    );
  }

  // For smaller datasets, use regular table
  if (data.length <= 100) {
    return (
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.key} className={col.hideOnMobile ? "hide-mobile" : ""}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((item, idx) => (
              <tr key={(item as any).id || idx}>
                {columns.map((col) => (
                  <td key={col.key} className={col.hideOnMobile ? "hide-mobile" : ""}>
                    {col.render(item)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // For larger datasets, use CSS-based virtualization
  return (
    <div
      ref={containerRef}
      className="virtual-table-container"
      style={{ maxHeight, overflow: "auto" }}
      role="table"
      aria-label="데이터 테이블"
    >
      <table className="data-table">
        <thead className="virtual-table-header">
          <tr>
            {columns.map((col) => (
              <th key={col.key} className={col.hideOnMobile ? "hide-mobile" : ""}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((item, idx) => (
            <tr key={(item as any).id || idx} style={{ height: rowHeight }}>
              {columns.map((col) => (
                <td key={col.key} className={col.hideOnMobile ? "hide-mobile" : ""}>
                  {col.render(item)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
