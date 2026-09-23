import "server-only";

import { createNeonAuth } from "@neondatabase/auth/next/server";

function required(name: "NEON_AUTH_BASE_URL" | "NEON_AUTH_COOKIE_SECRET"): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required for BCOS production authentication.`);
  return value;
}

export const auth = createNeonAuth({
  baseUrl: required("NEON_AUTH_BASE_URL"),
  cookies: {
    secret: required("NEON_AUTH_COOKIE_SECRET"),
    sessionDataTtl: 300,
  },
});
