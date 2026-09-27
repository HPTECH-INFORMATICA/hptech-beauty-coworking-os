import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const signIn = new URL("/auth/sign-in", request.url);
  signIn.searchParams.set("redirectTo", request.nextUrl.pathname + request.nextUrl.search);
  return NextResponse.redirect(signIn);
}

export const config = {
  matcher: ["/platform/:path*"],
};
