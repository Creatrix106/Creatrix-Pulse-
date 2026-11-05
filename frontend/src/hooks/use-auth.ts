"use client";

import { useMutation } from "@tanstack/react-query";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/stores/auth.store";

export function useLogin() {
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: authService.login,
    onSuccess: setUser,
  });
}

export function useRegister() {
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: authService.register,
    onSuccess: setUser,
  });
}

export function useLogout() {
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: authService.logout,
    onSettled: () => setUser(null),
  });
}
