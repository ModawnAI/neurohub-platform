"use client";

import { useCallback, useRef, useState } from "react";
import type { ZodSchema, ZodError } from "zod";

type FieldErrors<T> = Partial<Record<keyof T, string>>;

interface UseZodFormReturn<T extends Record<string, unknown>> {
  values: T;
  errors: FieldErrors<T>;
  setField: <K extends keyof T>(key: K, value: T[K]) => void;
  setValues: (partial: Partial<T>) => void;
  validate: () => T | null;
  validateField: (key: keyof T) => boolean;
  reset: (values?: T) => void;
  hasError: boolean;
}

export function useZodForm<T extends Record<string, unknown>>(
  schema: ZodSchema<T>,
  initial: T,
): UseZodFormReturn<T> {
  const [values, setValuesState] = useState<T>(initial);
  const [errors, setErrors] = useState<FieldErrors<T>>({});
  const initialRef = useRef(initial);

  const setField = useCallback(<K extends keyof T>(key: K, value: T[K]) => {
    setValuesState((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => {
      if (!prev[key]) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }, []);

  const setValues = useCallback((partial: Partial<T>) => {
    setValuesState((prev) => ({ ...prev, ...partial }));
  }, []);

  const validate = useCallback((): T | null => {
    const result = schema.safeParse(values);
    if (result.success) {
      setErrors({});
      return result.data;
    }
    const fieldErrors: FieldErrors<T> = {};
    for (const issue of (result.error as ZodError).issues) {
      const key = issue.path[0] as keyof T;
      if (key && !fieldErrors[key]) {
        fieldErrors[key] = issue.message;
      }
    }
    setErrors(fieldErrors);
    return null;
  }, [schema, values]);

  const validateField = useCallback(
    (key: keyof T): boolean => {
      const result = schema.safeParse(values);
      if (result.success) {
        setErrors((prev) => {
          if (!prev[key]) return prev;
          const next = { ...prev };
          delete next[key];
          return next;
        });
        return true;
      }
      const issue = (result.error as ZodError).issues.find(
        (i) => i.path[0] === key,
      );
      if (issue) {
        setErrors((prev) => ({ ...prev, [key]: issue.message }));
        return false;
      }
      setErrors((prev) => {
        if (!prev[key]) return prev;
        const next = { ...prev };
        delete next[key];
        return next;
      });
      return true;
    },
    [schema, values],
  );

  const reset = useCallback(
    (newValues?: T) => {
      setValuesState(newValues ?? initialRef.current);
      setErrors({});
    },
    [],
  );

  return {
    values,
    errors,
    setField,
    setValues,
    validate,
    validateField,
    reset,
    hasError: Object.keys(errors).length > 0,
  };
}
