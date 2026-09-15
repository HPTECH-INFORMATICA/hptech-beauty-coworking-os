import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AgendaPage from "../app/agenda/page";
import HomePage from "../app/page";
import {
  getBookings,
  getProfessionals,
  getResources,
  getUnits,
} from "../lib/bcos-api";

vi.mock("../lib/bcos-api", () => ({
  checkInBooking: vi.fn(),
  checkOutUsage: vi.fn(),
  closeManualInvoice: vi.fn(),
  confirmBooking: vi.fn(),
  confirmPixPayment: vi.fn(),
  createBooking: vi.fn(),
  getAvailability: vi.fn(),
  getBookings: vi.fn(),
  getProfessionals: vi.fn(),
  getResources: vi.fn(),
  getUnits: vi.fn(),
}));

const mockedGetUnits = vi.mocked(getUnits);
const mockedGetResources = vi.mocked(getResources);
const mockedGetProfessionals = vi.mocked(getProfessionals);
const mockedGetBookings = vi.mocked(getBookings);

beforeEach(() => {
  mockedGetUnits.mockResolvedValue([
    {
      id: "unit-1",
      name: "La Beauté Batel",
      timezone: "America/Sao_Paulo",
      active: true,
      created_at: "2026-09-15T00:00:00Z",
      updated_at: "2026-09-15T00:00:00Z",
    },
  ]);
  mockedGetResources.mockResolvedValue([]);
  mockedGetProfessionals.mockResolvedValue([]);
  mockedGetBookings.mockResolvedValue([]);
});

describe("operational navigation", () => {
  it("links the reception shell to real operational routes", async () => {
    render(await HomePage());
    expect(screen.getByRole("link", { name: "Agenda" })).toHaveAttribute("href", "/agenda");
    expect(screen.getByRole("link", { name: "Check-in" })).toHaveAttribute("href", "/check-in");
    expect(screen.getByRole("link", { name: "Financeiro" })).toHaveAttribute("href", "/financeiro");
    expect(screen.queryByText("CentralCheck-inFinanceiro")).not.toBeInTheDocument();
  });

  it("materializes agenda as a real route", async () => {
    render(await AgendaPage());
    expect(screen.getByRole("heading", { level: 1, name: "Agenda operacional" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voltar para a central" })).toHaveAttribute("href", "/");
  });

  it("exposes reservation creation from existing active resources and professionals", async () => {
    mockedGetResources.mockResolvedValue([
      { id: "resource-1", unit_id: "unit-1", category_id: "category-1", name: "Sala 01", operational_status: "AVAILABLE", buffer_before_minutes: 0, buffer_after_minutes: 0, active: true },
    ]);
    mockedGetProfessionals.mockResolvedValue([
      { id: "professional-1", external_user_id: null, name: "Profissional Homologação", email: null, phone: null, status: "ACTIVE" },
    ]);

    render(await AgendaPage());
    expect(screen.getByRole("button", { name: "Criar reserva" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Sala 01" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Profissional Homologação" })).toBeInTheDocument();
  });

  it("exposes confirmation for a pending reservation", async () => {
    mockedGetBookings.mockResolvedValue([
      { id: "booking-1", unit_id: "unit-1", resource_id: "resource-1", professional_id: "professional-1", series_id: null, status: "PENDING", starts_at: "2026-09-15T16:00:00Z", ends_at: "2026-09-15T17:00:00Z", buffer_before_minutes: 0, buffer_after_minutes: 0, pricing_snapshot: {} },
    ]);

    render(await AgendaPage());
    expect(screen.getByRole("button", { name: "Confirmar reserva" })).toBeInTheDocument();
  });
});
