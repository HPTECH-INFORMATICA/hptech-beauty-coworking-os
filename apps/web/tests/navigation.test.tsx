import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AgendaPage from "../app/agenda/page";
import AvailabilityPage from "../app/disponibilidade/page";
import HomePage from "../app/page";
import {
  getAvailability,
  getProfessionals,
  getReceptionAgenda,
  getReceptionNow,
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
  getProfessionals: vi.fn(),
  getReceptionAgenda: vi.fn(),
  getReceptionNow: vi.fn(),
  getResources: vi.fn(),
  getUnits: vi.fn(),
}));

const mockedGetUnits = vi.mocked(getUnits);
const mockedGetResources = vi.mocked(getResources);
const mockedGetProfessionals = vi.mocked(getProfessionals);
const mockedGetReceptionAgenda = vi.mocked(getReceptionAgenda);
const mockedGetReceptionNow = vi.mocked(getReceptionNow);
const mockedGetAvailability = vi.mocked(getAvailability);

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
  mockedGetReceptionAgenda.mockResolvedValue([]);
  mockedGetReceptionNow.mockResolvedValue({
    unit_id: "unit-1",
    generated_at: "2026-09-15T12:00:00Z",
    resources: [],
  });
  mockedGetAvailability.mockResolvedValue({ starts_at: "2026-09-15T16:00:00Z", ends_at: "2026-09-15T17:00:00Z", resources: [] });
});

describe("operational navigation", () => {
  it("links the reception shell to real operational routes", async () => {
    render(await HomePage());
    expect(screen.getByRole("link", { name: "Agenda" })).toHaveAttribute("href", "/agenda");
    expect(screen.getByRole("link", { name: "Check-in" })).toHaveAttribute("href", "/check-in");
    expect(screen.getByRole("link", { name: "Financeiro" })).toHaveAttribute("href", "/financeiro");
    expect(screen.getByRole("link", { name: "Meu portal" })).toHaveAttribute("href", "/profissional");
    expect(screen.queryByText("CentralCheck-inFinanceiro")).not.toBeInTheDocument();
  });

  it("materializes agenda as a real route", async () => {
    render(await AgendaPage());
    expect(screen.getByRole("heading", { level: 1, name: "Agenda operacional" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voltar para a central" })).toHaveAttribute("href", "/");
    expect(screen.getAllByRole("link", { name: /disponibilidade/i }).length).toBeGreaterThan(0);
  });

  it("materializes canonical availability as a visible route", async () => {
    mockedGetResources.mockResolvedValue([
      { id: "resource-1", unit_id: "unit-1", category_id: "category-1", name: "Sala 01", operational_status: "AVAILABLE", buffer_before_minutes: 0, buffer_after_minutes: 0, active: true },
    ]);
    render(await AvailabilityPage({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1, name: "Disponibilidade de espaços" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Consultar disponibilidade" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Sala 01" })).toBeInTheDocument();
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
    mockedGetReceptionAgenda.mockResolvedValue([
      {
        booking: { id: "booking-1", unit_id: "unit-1", resource_id: "resource-1", professional_id: "professional-1", series_id: null, status: "PENDING", starts_at: "2026-09-15T16:00:00Z", ends_at: "2026-09-15T17:00:00Z", buffer_before_minutes: 0, buffer_after_minutes: 0, pricing_snapshot: {} },
        usage: null,
      },
    ]);

    render(await AgendaPage());
    expect(screen.getByRole("button", { name: "Confirmar reserva" })).toBeInTheDocument();
  });
});
