import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HomePage from "../app/page";
import {
  getAccessResolution,
  getProfessionals,
  getReceptionAgenda,
  getReceptionNow,
  getUnits,
} from "../lib/bcos-api";

vi.mock("../lib/auth/server", () => ({ auth: { getSession: vi.fn().mockResolvedValue({ data: { session: {}, user: { id: "test-user" } } }) } }));

vi.mock("../lib/bcos-api", () => ({
  getAccessResolution: vi.fn(),
  getProfessionals: vi.fn(),
  getReceptionAgenda: vi.fn(),
  getReceptionNow: vi.fn(),
  getUnits: vi.fn(),
}));

const mockedGetAccessResolution = vi.mocked(getAccessResolution);
const mockedGetUnits = vi.mocked(getUnits);
const mockedGetProfessionals = vi.mocked(getProfessionals);
const mockedGetReceptionAgenda = vi.mocked(getReceptionAgenda);
const mockedGetReceptionNow = vi.mocked(getReceptionNow);

describe("HomePage", () => {
  beforeEach(() => {
    mockedGetAccessResolution.mockResolvedValue({ platform_destination: null, tenants: [{ tenant_id: "tenant-1", tenant_name: "La Beauté Batel", role: "RECEPTION", destination: "/" }] });
    mockedGetUnits.mockResolvedValue([
      {
        id: "unit-1",
        name: "La Beauté Batel - Homologação",
        timezone: "America/Sao_Paulo",
        active: true,
        created_at: "2026-09-12T00:00:00Z",
        updated_at: "2026-09-12T00:00:00Z",
      },
    ]);

    mockedGetReceptionNow.mockResolvedValue({
      unit_id: "unit-1",
      generated_at: "2026-09-15T12:00:00Z",
      resources: [
        {
          resource_id: "resource-1",
          resource_name: "Sala 01",
          operational_status: "AVAILABLE",
          booking_id: null,
          professional_id: null,
          starts_at: null,
          ends_at: null,
          usage_id: null,
          usage_status: null,
          checked_in_at: null,
          checked_out_at: null,
        },
      ],
    });

    mockedGetProfessionals.mockResolvedValue([
      {
        id: "professional-1",
        external_user_id: null,
        name: "Profissional Homologação",
        email: "homologacao@hptechinformatica.com",
        phone: null,
        status: "ACTIVE",
      },
    ]);

    mockedGetReceptionAgenda.mockResolvedValue([]);
  });

  it("renders the operational experience with canonical Reception data", async () => {
    render(await HomePage());

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "O que está acontecendo agora.",
      }),
    ).toBeInTheDocument();

    expect(screen.getAllByText("La Beauté Batel").length).toBeGreaterThan(0);
    expect(screen.getByText("Sala 01")).toBeInTheDocument();
    expect(screen.getByText("Profissional Homologação")).toBeInTheDocument();
    expect(screen.getByText("Operação conectada")).toBeInTheDocument();
    expect(screen.getByText("HPTECH PLATFORM")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Meu portal" })).toHaveAttribute(
      "href",
      "/profissional",
    );

    expect(
      screen.queryByText("La Beauté Batel - Homologação"),
    ).not.toBeInTheDocument();

    expect(screen.queryByText("Available")).not.toBeInTheDocument();
    expect(screen.queryByText("Completed")).not.toBeInTheDocument();
  });
});
