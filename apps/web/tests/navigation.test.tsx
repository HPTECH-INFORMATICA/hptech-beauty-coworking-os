import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AgendaPage from "../app/agenda/page";
import CheckInPage from "../app/check-in/page";
import AvailabilityPage from "../app/disponibilidade/page";
import HomePage from "../app/page";
import {
  getAvailability,
  getBookings,
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
  getBookings: vi.fn(),
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
const mockedGetBookings = vi.mocked(getBookings);

const activeResource = { id: "resource-1", unit_id: "unit-1", category_id: "category-1", name: "Sala 01", operational_status: "AVAILABLE", buffer_before_minutes: 0, buffer_after_minutes: 0, active: true };
const activeProfessional = { id: "professional-1", external_user_id: null, name: "Profissional Homologação", email: null, phone: null, status: "ACTIVE" };
const confirmedBooking = { id: "booking-1", unit_id: "unit-1", resource_id: "resource-1", professional_id: "professional-1", series_id: null, status: "CONFIRMED", starts_at: "2026-09-15T16:00:00Z", ends_at: "2026-09-15T17:00:00Z", buffer_before_minutes: 0, buffer_after_minutes: 0, pricing_snapshot: {} };

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
    mockedGetResources.mockResolvedValue([activeResource]);
    render(await AvailabilityPage({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1, name: "Disponibilidade de espaços" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Consultar disponibilidade" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Sala 01" })).toBeInTheDocument();
  });

  it("carries an available resource and period into reservation creation", async () => {
    mockedGetResources.mockResolvedValue([activeResource]);
    mockedGetAvailability.mockResolvedValue({ starts_at: "2026-09-15T16:00:00Z", ends_at: "2026-09-15T17:00:00Z", resources: [{ resource_id: "resource-1", available: true, reason: null }] });
    render(await AvailabilityPage({ searchParams: Promise.resolve({ starts_at: "2026-09-15T13:00", ends_at: "2026-09-15T14:00" }) }));
    expect(screen.getByRole("link", { name: "Reservar este espaço" })).toHaveAttribute("href", "/agenda?resource_id=resource-1&starts_at=2026-09-15T13%3A00&ends_at=2026-09-15T14%3A00");
  });

  it("prefills reservation fields received from availability", async () => {
    mockedGetResources.mockResolvedValue([activeResource]);
    mockedGetProfessionals.mockResolvedValue([activeProfessional]);
    render(await AgendaPage({ searchParams: Promise.resolve({ resource_id: "resource-1", starts_at: "2026-09-15T13:00", ends_at: "2026-09-15T14:00" }) }));
    expect(screen.getByRole("combobox", { name: "Espaço" })).toHaveValue("resource-1");
    expect(screen.getByLabelText("Início")).toHaveValue("2026-09-15T13:00");
    expect(screen.getByLabelText("Fim")).toHaveValue("2026-09-15T14:00");
  });

  it("exposes reservation creation from existing active resources and professionals", async () => {
    mockedGetResources.mockResolvedValue([activeResource]);
    mockedGetProfessionals.mockResolvedValue([activeProfessional]);

    render(await AgendaPage());
    expect(screen.getByRole("button", { name: "Criar reserva" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Sala 01" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Profissional Homologação" })).toBeInTheDocument();
  });

  it("exposes confirmation for a pending reservation", async () => {
    mockedGetReceptionAgenda.mockResolvedValue([
      {
        booking: { ...confirmedBooking, status: "PENDING" },
        usage: null,
      },
    ]);

    render(await AgendaPage());
    expect(screen.getByRole("button", { name: "Confirmar reserva" })).toBeInTheDocument();
  });

  it("links a confirmed reservation directly to its check-in", async () => {
    mockedGetReceptionAgenda.mockResolvedValue([{ booking: confirmedBooking, usage: null }]);
    render(await AgendaPage());
    expect(screen.getByRole("link", { name: "Ir para check-in" })).toHaveAttribute("href", "/check-in?booking=booking-1");
  });

  it("prioritizes the reservation selected by the agenda on check-in", async () => {
    mockedGetBookings.mockResolvedValue([
      { ...confirmedBooking, id: "booking-older", starts_at: "2026-09-15T15:00:00Z", ends_at: "2026-09-15T16:00:00Z" },
      confirmedBooking,
    ]);
    mockedGetResources.mockResolvedValue([activeResource]);
    mockedGetProfessionals.mockResolvedValue([activeProfessional]);

    render(await CheckInPage({ searchParams: Promise.resolve({ booking: "booking-1" }) }));
    const cards = screen.getAllByText(/RESERVA (SELECIONADA|CONFIRMADA)/);
    expect(cards[0]).toHaveTextContent("RESERVA SELECIONADA");
  });
});
