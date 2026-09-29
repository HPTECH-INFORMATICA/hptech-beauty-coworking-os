import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getSession: vi.fn(),
  getAccessResolution: vi.fn(),
  getPendingInvitations: vi.fn(),
}));

vi.mock("../lib/auth/server", () => ({ auth: { getSession: mocks.getSession } }));
vi.mock("../lib/bcos-api", () => ({
  getAccessResolution: mocks.getAccessResolution,
  getPendingInvitations: mocks.getPendingInvitations,
}));
vi.mock("../components/session-controls", () => ({
  SessionControls: ({ label }: { label: string }) => <div>{label}</div>,
}));

import AccessPage from "../app/acesso/page";

describe("contracting customer access state", () => {
  it("explains that an accepted invitation can still await HPTECH PLATFORM activation", async () => {
    mocks.getSession.mockResolvedValue({ data: { session: {}, user: { id: "owner-1", email: "owner@example.com" } } });
    mocks.getAccessResolution.mockResolvedValue({ platform_destination: null, tenants: [] });
    mocks.getPendingInvitations.mockResolvedValue([]);

    render(await AccessPage({ searchParams: Promise.resolve({ invitationAccepted: "pendingActivation" }) }));

    expect(screen.getByText("Convite aceito com sucesso.")).toBeInTheDocument();
    expect(screen.getByText(/aguarda liberação comercial pela HPTECH PLATFORM/i)).toBeInTheDocument();
    expect(screen.getByText("Nenhum acesso disponível")).toBeInTheDocument();
  });
});
