/**
 * Environment-driven configuration. The API base URL is the ONLY place a backend
 * location is defined; never hardcode URLs elsewhere.
 *
 *   NEXT_PUBLIC_API_BASE_URL  – backend root, e.g. https://api.creatrix.app/v1
 *   NEXT_PUBLIC_USE_MOCKS     – "false" switches every service to the real HTTP implementation
 */
export const env = {
  apiBaseUrl: (process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api").replace(/\/$/, ""),
  useMocks: process.env.NEXT_PUBLIC_USE_MOCKS !== "false",
} as const;
