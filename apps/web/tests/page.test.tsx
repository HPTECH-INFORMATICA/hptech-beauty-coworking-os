import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HomePage from "../app/page";
import {
  getBookings,
  getProfessionals,
  getResources,
  getUnits,
} from "../lib/bcos-api";

vi.mock("../lib/bcos-api", () => ({
  getBookings: vi.fn(),
  getProfessionals: vi.fn(),
  getResources: vi.fn(),
  getUnits: vi.fn(),
}));

const mockedGetUnits = vi.mocked(getUnits);
const mockedGetResources = vi.mocked(getResources);
const mockedGetProfessionals = vi.mocked(getProfessionals);
const mockedGetBookings = vi.mocked(getBookings);

describe("HomePage", () => {
  beforeEach(() => {
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

    mockedGetResources.mockResolvedValue([
      {
        id: "resource-1",
        unit_id: "unit-1",
        category_id: "category-1",
        name: "Sala 01",
        operational_status: "AVAILABLE",
        buffer_before_minutes: 0,
        buffer_after_minutes: 0,
        active: true,
      },
    ]);

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

    mockedGetBookings.mockResolvedValue([]);
  });

  it("renders the operational experience with real tenant data", async () => {
    const page = await HomePage();

    render(page);

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

    expect(
      screen.queryByText("La Beauté Batel - Homologação"),
    ).not.toBeInTheDocument();

    expect(screen.queryByText("Available")).not.toBeInTheDocument();
    expect(screen.queryByText("Completed")).not.toBeInTheDocument();
  });
});