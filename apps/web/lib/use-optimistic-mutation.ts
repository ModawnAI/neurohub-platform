"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/components/toast";

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
  successMessage = "저장되었습니다",
  errorMessage = "오류가 발생했습니다",
}: OptimisticMutationOptions<TData, TVariables>) {
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
      addToast("error", errorMessage);
    },
    onSuccess: () => {
      addToast("success", successMessage);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}
