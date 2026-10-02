import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProfessionalPage from "../app/profissional/page";
import { getMyBookings, getMyCommercialAvailability, getMyInvoices, getResourceCategories, getUnits } from "../lib/bcos-api";

vi.mock("../lib/bcos-api", () => ({ getMyBookings: vi.fn(), getMyInvoices: vi.fn(), getResourceCategories: vi.fn(), getUnits: vi.fn(), getMyCommercialAvailability: vi.fn(), createMyBooking: vi.fn() }));

const mockedGetMyBookings = vi.mocked(getMyBookings);
const mockedGetMyInvoices = vi.mocked(getMyInvoices);
const mockedGetMyCommercialAvailability = vi.mocked(getMyCommercialAvailability);
const mockedGetResourceCategories = vi.mocked(getResourceCategories);
const mockedGetUnits = vi.mocked(getUnits);

beforeEach(() => { mockedGetMyBookings.mockResolvedValue([]); mockedGetMyInvoices.mockResolvedValue([]); mockedGetResourceCategories.mockResolvedValue([]); mockedGetUnits.mockResolvedValue([]); });

describe("Professional Portal", () => {
  it("materializes own-scope bookings and invoices with business-facing labels", async () => {
    mockedGetMyBookings.mockResolvedValue([{ id: "booking-1", unit_id: "unit-1", resource_id: "resource-1", professional_id: "professional-1", series_id: null, status: "CONFIRMED", starts_at: "2026-09-16T12:00:00Z", ends_at: "2026-09-16T13:00:00Z", buffer_before_minutes: 0, buffer_after_minutes: 0, pricing_snapshot: {} }]);
    mockedGetMyInvoices.mockResolvedValue([{ id: "invoice-1", professional_id: "professional-1", source_usage_id: null, professional_billing_contract_id: null, billing_cycle_start: null, billing_cycle_end: null, manual_closed_at: null, status: "OPEN", currency: "BRL", subtotal_amount: "120.00", discount_amount: "0.00", total_amount: "120.00", created_at: "2026-09-15T12:00:00Z", updated_at: "2026-09-15T12:00:00Z" }]);

    render(await ProfessionalPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByRole("heading", { level: 1, name: "Minha operação" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Minhas reservas" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Minhas faturas" })).toBeInTheDocument();
    expect(screen.getByText("Confirmada")).toBeInTheDocument();
    expect(screen.getByText("Em aberto")).toBeInTheDocument();
    expect(screen.getAllByText(/R\$\s*120,00/)).toHaveLength(2);
    expect(screen.queryByText("booking-1")).not.toBeInTheDocument();
    expect(screen.queryByText("invoice-1")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voltar para a central" })).toHaveAttribute("href", "/");
  });
  it("converts the selected unit local time to UTC before commercial availability", async () => {
    mockedGetUnits.mockResolvedValue([{ id: "unit-1", name: "Batel", timezone: "America/Sao_Paulo", active: true }]);
    mockedGetResourceCategories.mockResolvedValue([]);
    mockedGetMyCommercialAvailability.mockResolvedValue({ unit_id: "unit-1", starts_at: "2026-10-02T16:00:00.000Z", ends_at: "2026-10-02T17:00:00.000Z", resources: [{ resource_id: "resource-1", resource_name: "Sala 01", resource_category_id: "category-1", available: true, unavailable_reason: null, pricing_snapshot: {}, price_amount: "120.00", price_currency: "BRL", price_modality: "HOURLY" }] });

    render(await ProfessionalPage({ searchParams: Promise.resolve({ unit_id: "unit-1", starts_at: "2026-10-02T13:00", ends_at: "2026-10-02T14:00" }) }));

    expect(mockedGetMyCommercialAvailability).toHaveBeenCalledWith({ unitId: "unit-1", startsAt: "2026-10-02T16:00:00.000Z", endsAt: "2026-10-02T17:00:00.000Z", categoryId: undefined });
    expect(screen.getByText("Valor (por hora)")).toBeInTheDocument();
  });

});
