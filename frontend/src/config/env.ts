/**
 * Environment-driven configuration. The API base URL is the ONLY place a backend
 * location is defined; never hardcode URLs elsewhere.
 *
 *   NEXT_PUBLIC_API_BASE_URL  – backend root, e.g. https://api.creatrix.app/v1
 */
export const env = {
  apiBaseUrl: (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1").replace(/\/$/, ""),
} as const;