import "server-only";

import { createNeonAuth } from "@neondatabase/auth/next/server";

type NeonAuth = ReturnType<typeof createNeonAuth>;

let authInstance: NeonAuth | undefined;

function required(name: "NEON_AUTH_BASE_URL" | "NEON_AUTH_COOKIE_SECRET"): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required for BCOS production authentication.`);
  return value;
}

function getAuth(): NeonAuth {
  if (!authInstance) {
    authInstance = createNeonAuth({
      baseUrl: required("NEON_AUTH_BASE_URL"),
      cookies: {
        secret: required("NEON_AUTH_COOKIE_SECRET"),
        sessionDataTtl: 300,
      },
    });
  }
  return authInstance;
}

/**
 * Lazily resolves Neon Auth so Next.js/Vercel can analyze route modules during
 * Preview builds without requiring Production-only credentials. Any real auth
 * operation still resolves the required configuration and fails closed when it
 * is unavailable.
 */
export const auth = {
  getSession: (...args: Parameters<NeonAuth["getSession"]>) => getAuth().getSession(...args),
  token: (...args: Parameters<NeonAuth["token"]>) => getAuth().token(...args),
  handler: () => {
    const handle = async (request: Request) => {
      const handlers = getAuth().handler();
      const method = request.method as keyof typeof handlers;
      const handler = handlers[method];

      if (typeof handler !== "function") {
        return new Response("Method Not Allowed", {
          status: 405,
          headers: { Allow: "GET, POST, PUT, DELETE, PATCH" },
        });
      }

      return handler(request);
    };

    return {
      GET: handle,
      POST: handle,
      PUT: handle,
      DELETE: handle,
      PATCH: handle,
    };
  },
};
