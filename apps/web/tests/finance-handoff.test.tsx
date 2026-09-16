import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import FinancePage from "../app/financeiro/page";
import { getInvoice, getInvoices, getProfessionals } from "../lib/bcos-api";

vi.mock("../lib/bcos-api", () => ({
  closeManualInvoice: vi.fn(),
  confirmPixPayment: vi.fn(),
  getInvoice: vi.fn(),
  getInvoices: vi.fn(),
  getProfessionals: vi.fn(),
}));

const mockedGetInvoices = vi.mocked(getInvoices);
const mockedGetInvoice = vi.mocked(getInvoice);
const mockedGetProfessionals = vi.mocked(getProfessionals);

const accumulatedInvoice = {
  id: "invoice-accumulated",
  professional_id: "professional-1",
  source_usage_id: null,
  professional_billing_contract_id: "contract-1",
  billing_cycle_start: "2026-09-01T03:00:00Z",
  billing_cycle_end: "2026-10-01T03:00:00Z",
  manual_closed_at: null,
  status: "OPEN",
  currency: "BRL",
  subtotal_amount: "100.00",
  discount_amount: "0.00",
  total_amount: "100.00",
  created_at: "2026-09-01T03:00:00Z",
  updated_at: "2026-09-15T17:00:00Z",
};

beforeEach(() => {
  mockedGetInvoices.mockResolvedValue([]);
  mockedGetProfessionals.mockResolvedValue([]);
  mockedGetInvoice.mockReset();
});

describe("checkout billing handoff", () => {
  it("shows the asynchronous processing state while the completed usage has no materialized billing effect", async () => {
    render(await FinancePage({ searchParams: Promise.resolve({ usage: "usage-1" }) }));

    expect(screen.getByText("Uso finalizado. Cobrança em processamento.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Atualizar financeiro" })).toHaveAttribute("href", "/financeiro?usage=usage-1");
    expect(screen.queryByText("Nenhuma fatura encontrada")).not.toBeInTheDocument();
  });

  it("recognizes a completed usage inside an accumulated invoice item", async () => {
    mockedGetInvoices.mockResolvedValue([accumulatedInvoice]);
    mockedGetInvoice.mockResolvedValue({
      ...accumulatedInvoice,
      items: [
        {
          id: "item-1",
          usage_id: "usage-1",
          item_type: "BASE_LEASE",
          description: "Locação base",
          quantity: "1",
          unit_amount: "100.00",
          total_amount: "100.00",
          billing_period_start: null,
          billing_period_end: null,
          related_invoice_item_id: null,
          created_at: "2026-09-15T17:00:00Z",
        },
      ],
      confirmed_amount: "0.00",
      remaining_amount: "100.00",
    });

    render(await FinancePage({ searchParams: Promise.resolve({ usage: "usage-1" }) }));

    expect(screen.getByText("COBRANÇA DO USO FINALIZADO")).toBeInTheDocument();
    expect(screen.queryByText("Uso finalizado. Cobrança em processamento.")).not.toBeInTheDocument();
  });
});
