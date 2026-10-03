import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AgendaPage from "../app/agenda/page";
import { getProfessionals, getReceptionAgenda, getResources, getUnits } from "../lib/bcos-api";

vi.mock("../app/operations/actions", () => ({ confirmBookingAction: vi.fn(), createBookingAction: vi.fn() }));
vi.mock("../lib/auth/authorization", () => ({ requireTenantPermission: vi.fn().mockResolvedValue({ permissions: ["AGENDA_VIEW","AGENDA_MANAGE","FINANCE_VIEW","FINANCE_MANAGE"] }) }));
vi.mock("../lib/bcos-api", () => ({ getProfessionals: vi.fn(), getReceptionAgenda: vi.fn(), getResources: vi.fn(), getUnits: vi.fn() }));

const mockedGetUnits = vi.mocked(getUnits);
const mockedGetProfessionals = vi.mocked(getProfessionals);
const mockedGetResources = vi.mocked(getResources);
const mockedGetReceptionAgenda = vi.mocked(getReceptionAgenda);

describe("Agenda multiunit", () => {
  beforeEach(() => {
    mockedGetUnits.mockResolvedValue([
      { id: "unit-1", name: "Batel", timezone: "America/Sao_Paulo", active: true, created_at: "2026-10-01T12:00:00Z", updated_at: "2026-10-01T12:00:00Z" },
      { id: "unit-2", name: "Centro", timezone: "America/Sao_Paulo", active: true, created_at: "2026-10-01T12:00:00Z", updated_at: "2026-10-01T12:00:00Z" },
    ]);
    mockedGetProfessionals.mockResolvedValue([]);
    mockedGetResources.mockResolvedValue([]);
    mockedGetReceptionAgenda.mockResolvedValue([]);
  });

  it("loads the explicitly selected unit instead of hiding bookings in other units", async () => {
    render(await AgendaPage({ searchParams: Promise.resolve({ unit_id: "unit-2" }) }));
    expect(screen.getByRole("combobox", { name: "Unidade" })).toHaveValue("unit-2");
    expect(mockedGetResources).toHaveBeenCalledWith("unit-2");
    expect(mockedGetReceptionAgenda).toHaveBeenCalledWith(expect.objectContaining({ unitId: "unit-2" }));
  });
});
