"use client";

import { useEffect } from "react";

const BROWSER_SESSION_MARKER = "bcos_browser_session";

export function BrowserSessionBoundary() {
  useEffect(() => {
    const marker = sessionStorage.getItem(BROWSER_SESSION_MARKER);
    if (marker) return;

    sessionStorage.setItem(BROWSER_SESSION_MARKER, "active");

    void fetch("/api/auth/sign-out", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    }).finally(() => {
      window.location.replace("/auth/sign-in");
    });
  }, []);

  return null;
}
