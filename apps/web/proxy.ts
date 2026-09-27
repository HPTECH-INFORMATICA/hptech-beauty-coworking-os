import { NextRequest, NextResponse } from "next/server";

const AUTH_COOKIE_HINTS = ["neon-auth", "better-auth", "session"];

export function proxy(request: NextRequest) {
  const hasAuthCookie = request.cookies.getAll().some(({ name, value }) => {
    const normalized = name.toLowerCase();
    return Boolean(value) && AUTH_COOKIE_HINTS.some((hint) => normalized.includes(hint));
  });

  if (!hasAuthCookie) {
    const signIn = new URL("/auth/sign-in", request.url);
    signIn.searchParams.set("redirectTo", request.nextUrl.pathname + request.nextUrl.search);
    return NextResponse.redirect(signIn);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/platform/:path*"],
};
