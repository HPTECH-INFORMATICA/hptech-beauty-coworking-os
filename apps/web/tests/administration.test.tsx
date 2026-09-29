import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TenantAdministrationPage from "../app/administracao/page";
import UsersAdminPage from "../app/administracao/usuarios/page";
import {
  getPricingRules,
  getProfessionals,
  getReceptionHours,
  getResourceCategories,
  getResources,
  getTenantMemberships,
  getTenantProfile,
  getUnits,
} from "../lib/bcos-api";

vi.mock("../lib/bcos-api", () => ({
  getPricingRules: vi.fn(),
  getProfessionals: vi.fn(),
  getReceptionHours: vi.fn(),
  getResourceCategories: vi.fn(),
  getResources: vi.fn(),
  getTenantMemberships: vi.fn(),
  getTenantProfile: vi.fn(),
  getUnits: vi.fn(),
}));

const mockedGetUnits = vi.mocked(getUnits);
const mockedGetReceptionHours = vi.mocked(getReceptionHours);

describe("tenant administration", () => {
  beforeEach(() => {
    vi.mocked(getTenantProfile).mockResolvedValue({ legal_name: "La Beauté Ltda", trade_name: "La Beauté", tax_id: null, email: "contato@example.com", phone: null });
    mockedGetUnits.mockResolvedValue([
      { id: "unit-1", name: "Batel", timezone: "America/Sao_Paulo", active: true, created_at: "", updated_at: "" },
      { id: "unit-2", name: "Centro", timezone: "America/Sao_Paulo", active: true, created_at: "", updated_at: "" },
    ]);
    vi.mocked(getResourceCategories).mockResolvedValue([]);
    vi.mocked(getResources).mockResolvedValue([]);
    vi.mocked(getProfessionals).mockResolvedValue([]);
    vi.mocked(getPricingRules).mockResolvedValue([]);
    mockedGetReceptionHours.mockImplementation(async (unitId) => unitId === "unit-1"
      ? [{ day_of_week: 0, opens_at: "08:00:00", closes_at: "18:00:00", is_closed: false }]
      : [{ day_of_week: 0, opens_at: "09:00:00", closes_at: "17:00:00", is_closed: false }]);
    vi.mocked(getTenantMemberships).mockResolvedValue([]);
  });

  it("loads and renders reception hours for every unit", async () => {
    render(await TenantAdministrationPage());
    expect(mockedGetReceptionHours).toHaveBeenCalledWith("unit-1");
    expect(mockedGetReceptionHours).toHaveBeenCalledWith("unit-2");
    expect(screen.getByRole("button", { name: "Salvar horários de Batel" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar horários de Centro" })).toBeInTheDocument();
  });

  it("renders users as administration content without a legacy product shell", async () => {
    render(await UsersAdminPage({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1, name: "Usuários e acessos" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Configurações" })).toHaveAttribute("href", "/administracao");
    expect(document.querySelector(".tenant-admin-shell")).not.toBeInTheDocument();
  });
});
