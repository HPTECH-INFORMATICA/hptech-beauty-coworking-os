import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProfessionalPage from "../app/profissional/page";
import { getMyBookings, getMyInvoices } from "../lib/bcos-api";

vi.mock("../lib/bcos-api", () => ({
  getMyBookings: vi.fn(),
  getMyInvoices: vi.fn(),
}));

const mockedGetMyBookings = vi.mocked(getMyBookings);
const mockedGetMyInvoices = vi.mocked(getMyInvoices);

beforeEach(() => {
  mockedGetMyBookings.mockResolvedValue([]);
  mockedGetMyInvoices.mockResolvedValue([]);
});

describe("Professional Portal", () => {
  it("materializes own-scope bookings and invoices as a visible route", async () => {
    mockedGetMyBookings.mockResolvedValue([
      {
        id: "booking-1",
        unit_id: "unit-1",
        resource_id: "resource-1",
        professional_id: "professional-1",
        series_id: null,
        status: "CONFIRMED",
        starts_at: "2026-09-16T12:00:00Z",
        ends_at: "2026-09-16T13:00:00Z",
        buffer_before_minutes: 0,
        buffer_after_minutes: 0,
        pricing_snapshot: {},
      },
    ]);
    mockedGetMyInvoices.mockResolvedValue([
      {
        id: "invoice-1",
        professional_id: "professional-1",
        source_usage_id: null,
        professional_billing_contract_id: null,
        billing_cycle_start: null,
        billing_cycle_end: null,
        manual_closed_at: null,
        status: "OPEN",
        currency: "BRL",
        subtotal_amount: "120.00",
        discount_amount: "0.00",
        total_amount: "120.00",
        created_at: "2026-09-15T12:00:00Z",
        updated_at: "2026-09-15T12:00:00Z",
      },
    ]);

    render(await ProfessionalPage());

    expect(screen.getByRole("heading", { level: 1, name: "Minha operação" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Minhas reservas" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Minhas faturas" })).toBeInTheDocument();
    expect(screen.getAllByText(/R\$\s*120,00/)).toHaveLength(2);
    expect(screen.getByRole("link", { name: "Voltar para a central" })).toHaveAttribute("href", "/");
  });
});
