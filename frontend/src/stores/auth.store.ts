"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/types/auth";

interface AuthState {
  user: User | null;
  setUser: (user: User | null) => void;
}

/** Holds the signed-in user for UI purposes. Real session security belongs to the backend (httpOnly cookie). */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user) => set({ user }),
    }),
    { name: "cp-auth", skipHydration: true },
  ),
);
