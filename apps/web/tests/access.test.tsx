import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getSession: vi.fn(),
  getAccessResolution: vi.fn(),
  getPendingInvitations: vi.fn(),
  getPendingProfessionalInvitations: vi.fn(),
  getPendingTeamInvitations: vi.fn(),
}));

vi.mock("../lib/auth/server", () => ({ auth: { getSession: mocks.getSession } }));
vi.mock("../lib/bcos-api", () => ({
  getAccessResolution: mocks.getAccessResolution,
  getPendingInvitations: mocks.getPendingInvitations,
  getPendingProfessionalInvitations: mocks.getPendingProfessionalInvitations,
  getPendingTeamInvitations: mocks.getPendingTeamInvitations,
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
    mocks.getPendingProfessionalInvitations.mockResolvedValue([]);
    mocks.getPendingTeamInvitations.mockResolvedValue([]);

    render(await AccessPage({ searchParams: Promise.resolve({ invitationAccepted: "pendingActivation" }) }));

    expect(screen.getByText("Convite aceito com sucesso.")).toBeInTheDocument();
    expect(screen.getByText(/aguarda liberação comercial pela HPTECH PLATFORM/i)).toBeInTheDocument();
    expect(screen.getByText("Nenhum acesso disponível")).toBeInTheDocument();
  });

  it("shows an email-matched professional invitation before portal access", async () => {
    mocks.getSession.mockResolvedValue({ data: { session: {}, user: { id: "pro-1", email: "cris@example.com" } } });
    mocks.getAccessResolution.mockResolvedValue({ platform_destination: null, tenants: [] });
    mocks.getPendingInvitations.mockResolvedValue([]);
    mocks.getPendingTeamInvitations.mockResolvedValue([]);
    mocks.getPendingProfessionalInvitations.mockResolvedValue([{ id: "invite-1", tenant_id: "tenant-1", tenant_name: "LA BEAUTE", professional_id: "professional-1", professional_name: "Cristiana", email: "cris@example.com", status: "PENDING", expires_at: "2026-10-09T12:00:00Z" }]);

    render(await AccessPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Seu portal profissional está disponível")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Cristiana · Revisar/ })).toHaveAttribute("href", "/acesso/profissionais/invite-1");
  });
  it("keeps a valid team invitation visible when another access lookup fails", async () => {
    mocks.getSession.mockResolvedValue({ data: { session: {}, user: { id: "team-1", email: "pedro@example.com" } } });
    mocks.getAccessResolution.mockRejectedValue(new Error("access lookup unavailable"));
    mocks.getPendingInvitations.mockResolvedValue([]);
    mocks.getPendingProfessionalInvitations.mockResolvedValue([]);
    mocks.getPendingTeamInvitations.mockResolvedValue([{ id: "team-invite-1", tenant_id: "tenant-1", tenant_name: "LA BEAUTE", display_name: "Pedro Sales", email: "pedro@example.com", role: "RECEPTION", status: "PENDING", expires_at: "2026-10-12T12:00:00Z" }]);

    render(await AccessPage({ searchParams: Promise.resolve({}) }));

    expect(screen.queryByText("Acesso temporariamente indisponível")).not.toBeInTheDocument();
    expect(screen.getByText("Você foi convidado para uma equipe")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Pedro Sales · RECEPTION/ })).toHaveAttribute("href", "/acesso/equipe/team-invite-1");
  });

});
