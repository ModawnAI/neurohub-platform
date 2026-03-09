"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/components/toast";
import { useTranslation } from "@/lib/i18n";

interface OptimisticMutationOptions<TData, TVariables> {
  mutationFn: (variables: TVariables) => Promise<TData>;
  queryKey: string[];
  onOptimisticUpdate?: (variables: TVariables, oldData: unknown) => unknown;
  successMessage?: string;
  errorMessage?: string;
}

export function useOptimisticMutation<TData, TVariables>({
  mutationFn,
  queryKey,
  onOptimisticUpdate,
  successMessage,
  errorMessage,
}: OptimisticMutationOptions<TData, TVariables>) {
  const { t } = useTranslation();
  const resolvedSuccess = successMessage ?? t("toast.saveSuccess");
  const resolvedError = errorMessage ?? t("toast.genericError");
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  return useMutation({
    mutationFn,
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey });
      const previousData = queryClient.getQueryData(queryKey);

      if (onOptimisticUpdate) {
        queryClient.setQueryData(queryKey, (old: unknown) =>
          onOptimisticUpdate(variables, old)
        );
      }

      return { previousData };
    },
    onError: (_err, _variables, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
      addToast("error", resolvedError);
    },
    onSuccess: () => {
      addToast("success", resolvedSuccess);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}
