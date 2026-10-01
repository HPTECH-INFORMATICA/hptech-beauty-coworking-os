import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { pricingRuleDefinitionFromForm } from "../app/administracao/pricing-form";

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
    vi.mocked(getResourceCategories).mockResolvedValue([{ id: "category-1", name: "Sala de estética", active: true }]);
    vi.mocked(getResources).mockResolvedValue([{ id: "resource-1", unit_id: "unit-1", category_id: "category-1", name: "Sala 01", operational_status: "AVAILABLE", buffer_before_minutes: 0, buffer_after_minutes: 0, active: true }]);
    vi.mocked(getProfessionals).mockResolvedValue([{ id: "professional-1", external_user_id: null, name: "Cristiana", email: "cris@example.com", phone: null, profession: "Enfermeira Esteta", council_type: "COREN", council_number: "PR 451.408", status: "ACTIVE" }]);
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
    expect(screen.getAllByRole("button", { name: "Salvar horários" })).toHaveLength(2);
    const mondayOpens = screen.getAllByLabelText("Segunda abre");
    const mondayCloses = screen.getAllByLabelText("Segunda fecha");
    expect(mondayOpens).toHaveLength(2);
    expect(mondayCloses).toHaveLength(2);
    expect(mondayOpens[0]).toHaveValue("08:00");
    expect(mondayCloses[0]).toHaveValue("18:00");
    expect(screen.getByRole("heading", { level: 1, name: "Configurações do coworking" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Áreas de configuração" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Usuários.*Acessos e permissões/i })).toHaveAttribute("href", "/administracao/usuarios");
    expect(screen.getByText("Regras comerciais")).toBeInTheDocument();
    expect(screen.getByText("Como configurar")).toBeInTheDocument();
    expect(screen.getByText(/prioridade serve para desempatar regras aplicáveis/i)).toBeInTheDocument();
    expect(screen.getByText(/dispensar a cobrança do excedente/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Salvar unidade" })).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Salvar espaço" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar profissional" })).toBeInTheDocument();
    expect(screen.getByText("Sala 01")).toBeInTheDocument();
    expect(screen.getByText("Cristiana")).toBeInTheDocument();
    expect(screen.getByText(/Enfermeira Esteta/)).toBeInTheDocument();
    expect(screen.getByText("1. Tipos de espaço")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar tipo" })).toBeInTheDocument();
    expect(screen.getByText("Excluir tipo de espaço")).toBeInTheDocument();
    expect(screen.getByText("2. Espaços da unidade")).toBeInTheDocument();
    expect(screen.getAllByText("Configurar semana")).toHaveLength(2);
    expect(screen.getAllByText("Ativa", { selector: "span" })).toHaveLength(2);
    expect(screen.getAllByText("Ativo", { selector: "span" })).toHaveLength(3);
  });

  it("renders existing pricing rules with edit and safe removal controls", async () => {
    vi.mocked(getPricingRules).mockResolvedValue([{
      id: "rule-1", unit_id: "unit-1", resource_category_id: "category-1",
      name: "SALA 01 - HORA", status: "ACTIVE", priority: 100, currency: "BRL",
      rule_definition: { schema_version: 1, modality: "HOURLY", base_price_amount: "39.00", overtime: { hourly_price_amount: "39.00", proportional_until_minutes: 29, full_hour_from_minutes: 30, forgiveness_allowed: false } },
      valid_from: null, valid_until: null,
    }]);
    render(await TenantAdministrationPage());
    expect(screen.getByText("SALA 01 - HORA")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar regra" })).toBeInTheDocument();
    expect(screen.getByText("Excluir regra de preço")).toBeInTheDocument();
    expect(screen.getByText(/Reservas já criadas preservam o snapshot de preço/)).toBeInTheDocument();
  });

  it("renders users as administration content without a legacy product shell", async () => {
    render(await UsersAdminPage({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1, name: "Usuários e acessos" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Configurações" })).toHaveAttribute("href", "/administracao");
    expect(document.querySelector(".tenant-admin-shell")).not.toBeInTheDocument();
  });
  it("maps the commercial pricing form to the frozen V1 definition", () => {
    const form = new FormData();
    form.set("modality", "HOURLY");
    form.set("base_price_amount", "120.00");
    form.set("overtime_hourly_price_amount", "150.00");
    form.set("proportional_until_minutes", "29");
    form.set("full_hour_from_minutes", "30");
    form.set("forgiveness_allowed", "on");

    expect(pricingRuleDefinitionFromForm(form)).toEqual({
      schema_version: 1,
      modality: "HOURLY",
      base_price_amount: "120.00",
      overtime: {
        hourly_price_amount: "150.00",
        proportional_until_minutes: 29,
        full_hour_from_minutes: 30,
        forgiveness_allowed: true,
      },
    });
  });
});
