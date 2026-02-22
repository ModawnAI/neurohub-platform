"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listNotifications, markNotificationRead, markAllNotificationsRead, type NotificationRead } from "@/lib/api";

export function useNotifications() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => listNotifications(),
    refetchInterval: 30_000,
  });

  const notifications = data?.items ?? [];
  const unreadCount = notifications.filter((n: NotificationRead) => !n.is_read).length;

  const markRead = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const markAllRead = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  return {
    notifications,
    unreadCount,
    isLoading,
    markRead: markRead.mutate,
    markAllRead: markAllRead.mutate,
  };
}
