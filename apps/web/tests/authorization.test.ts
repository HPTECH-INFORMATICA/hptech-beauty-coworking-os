import { describe, expect, it, vi } from "vitest";

const redirect = vi.fn((path: string) => { throw new Error(`REDIRECT:${path}`); });
const getSession = vi.fn();
const getAccessResolution = vi.fn();
const cookieGet = vi.fn();

vi.mock("next/navigation", () => ({ redirect }));
vi.mock("next/headers", () => ({ cookies: vi.fn(async () => ({ get: cookieGet })) }));
vi.mock("../lib/auth/server", () => ({ auth: { getSession } }));
vi.mock("../lib/bcos-api", () => ({ getAccessResolution }));

import { requireTenantRole } from "../lib/auth/authorization";

describe("selected tenant authorization", () => {
  it("returns the tenant selected by the authenticated customer", async () => {
    getSession.mockResolvedValue({ data: { session: {}, user: { id: "user-1" } } });
    cookieGet.mockReturnValue({ value: "tenant-b" });
    getAccessResolution.mockResolvedValue({
      platform_destination: null,
      tenants: [
        { tenant_id: "tenant-a", tenant_name: "Outro cliente", role: "OWNER", destination: "/" },
        { tenant_id: "tenant-b", tenant_name: "LA BEAUTE", role: "ADMIN", destination: "/" },
      ],
    });

    await expect(requireTenantRole(["OWNER", "ADMIN"])).resolves.toMatchObject({
      tenant_id: "tenant-b",
      tenant_name: "LA BEAUTE",
      role: "ADMIN",
    });
  });

  it("rejects a selected tenant when its role cannot enter the requested area", async () => {
    getSession.mockResolvedValue({ data: { session: {}, user: { id: "user-1" } } });
    cookieGet.mockReturnValue({ value: "tenant-b" });
    getAccessResolution.mockResolvedValue({
      platform_destination: null,
      tenants: [{ tenant_id: "tenant-b", tenant_name: "LA BEAUTE", role: "PROFESSIONAL", destination: "/profissional" }],
    });

    await expect(requireTenantRole(["OWNER", "ADMIN"])).rejects.toThrow("REDIRECT:/acesso");
  });
});
