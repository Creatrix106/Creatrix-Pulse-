import { env } from "@/config/env";
import type { LoginPayload, RegisterPayload, User } from "@/types/auth";
import { apiClient, ApiError } from "./api-client";
import { delay } from "./mock/utils";

/**
 * BACKEND INTEGRATION POINT – authentication
 *   POST /auth/login     (LoginPayload)    -> User   (sets httpOnly session cookie)
 *   POST /auth/register  (RegisterPayload) -> User
 *   POST /auth/logout                      -> 204
 *   GET  /auth/me                          -> User   (401 when signed out)
 */
export interface AuthService {
  login(payload: LoginPayload): Promise<User>;
  register(payload: RegisterPayload): Promise<User>;
  logout(): Promise<void>;
}

const httpAuthService: AuthService = {
  login: (payload) => apiClient.post<User>("/auth/login", payload),
  register: (payload) => apiClient.post<User>("/auth/register", payload),
  logout: () => apiClient.post<void>("/auth/logout"),
};

/** Mock only: accepts any well-formed credentials. There is no real authentication here. */
const mockAuthService: AuthService = {
  async login({ email }) {
    await delay(500);
    if (email.toLowerCase().startsWith("blocked@")) {
      throw new ApiError(401, { code: "invalid_credentials", message: "Incorrect email or password." });
    }
    const name = email.split("@")[0].replace(/[._-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    return { id: "user-demo", name, email, role: "admin" };
  },
  async register({ name, email }) {
    await delay(600);
    return { id: `user-${Date.now().toString(36)}`, name, email, role: "admin" };
  },
  async logout() {
    await delay(150);
  },
};

export const authService: AuthService = env.useMocks ? mockAuthService : httpAuthService;
