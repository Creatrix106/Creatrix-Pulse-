"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/stores/auth.store";
import { isApiError } from "@/services/api-client";
import { toast } from "@/stores/toast.store";

export const authKey = ["auth", "me"] as const;

export function useCurrentUser() {
  const setUser = useAuthStore((s) => s.setUser);
  return useQuery({
    queryKey: authKey,
    queryFn: async () => {
      try {
        const user = await authService.me();
        setUser(user);
        return user;
      } catch (error) {
        if (isApiError(error) && error.status === 401) setUser(null);
        throw error;
      }
    },
    retry: (count, error) => !(isApiError(error) && error.status >= 400 && error.status < 500) && count < 2,
    staleTime: 60_000,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: authService.login,
    onSuccess: (user) => {
      setUser(user);
      queryClient.setQueryData(authKey, user);
    },
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: authService.register,
    onSuccess: (user) => {
      setUser(user);
      queryClient.setQueryData(authKey, user);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: authService.logout,
    onSuccess: () => {
      setUser(null);
      queryClient.setQueryData(authKey, null);
    },
    onError: () => toast.error("Could not sign out", "Please try again."),
  });
}
