"use client";

import clsx from "clsx";

interface TypeOption<T> {
  value: T;
  icon: React.ReactNode;
  title: string;
  description: string;
}

interface TypeSelectorProps<T extends string> {
  options: TypeOption<T>[];
  selected: T | null;
  onSelect: (value: T) => void;
}

export function TypeSelector<T extends string>({ options, selected, onSelect }: TypeSelectorProps<T>) {
  return (
    <div className="type-selector-grid">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          className={clsx("type-selector-card", selected === opt.value && "selected")}
          onClick={() => onSelect(opt.value)}
        >
          <div className="type-selector-icon">{opt.icon}</div>
          <p className="type-selector-title">{opt.title}</p>
          <p className="type-selector-desc">{opt.description}</p>
        </button>
      ))}
    </div>
  );
}
