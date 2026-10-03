import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { pricingRuleDefinitionFromForm } from "../app/administracao/pricing-form";

import TenantAdministrationPage from "../app/administracao/page";
import UsersAdminPage from "../app/administracao/usuarios/page";
import {
  getPricingRules,
  getProfessionalOnboardingRequests,
  getTenantOnboardingDocuments,
  getProfessionals,
  getReceptionHours,
  getResourceCategories,
  getResources,
  getTenantMembershipPermissions,
  getTenantMemberships,
  getTenantProfile,
  getUnits,
} from "../lib/bcos-api";

vi.mock("../lib/auth/authorization", () => ({ requireTenantPermission: vi.fn().mockResolvedValue({}) }));

vi.mock("../lib/bcos-api", () => ({
  getPricingRules: vi.fn(),
  getProfessionalOnboardingRequests: vi.fn(),
  getTenantOnboardingDocuments: vi.fn(),
  getProfessionals: vi.fn(),
  getReceptionHours: vi.fn(),
  getResourceCategories: vi.fn(),
  getResources: vi.fn(),
  getTenantMembershipPermissions: vi.fn(),
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
    vi.mocked(getProfessionalOnboardingRequests).mockResolvedValue([]);
    vi.mocked(getTenantOnboardingDocuments).mockResolvedValue([]);
    mockedGetReceptionHours.mockImplementation(async (unitId) => unitId === "unit-1"
      ? [{ day_of_week: 0, opens_at: "08:00:00", closes_at: "18:00:00", is_closed: false }]
      : [{ day_of_week: 0, opens_at: "09:00:00", closes_at: "17:00:00", is_closed: false }]);
    vi.mocked(getTenantMemberships).mockResolvedValue([]);
    vi.mocked(getTenantMembershipPermissions).mockResolvedValue([]);
  });

  it("presents administration as focused submodules instead of one long page", async () => {
    render(await TenantAdministrationPage());
    expect(screen.getByRole("heading", { level: 1, name: "Configurações do coworking" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Submenu da administração" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Empresa.*Dados do negócio/i })).toHaveAttribute("href", "/administracao?area=empresa");
    expect(screen.getByRole("link", { name: /Unidades.*2 locais/i })).toHaveAttribute("href", "/administracao?area=unidades");
    expect(screen.getByRole("link", { name: /Profissionais.*1 vinculados/i })).toHaveAttribute("href", "/administracao?area=profissionais");
    expect(screen.getByRole("link", { name: /Usuários.*Acessos e permissões/i })).toHaveAttribute("href", "/administracao/usuarios");
    expect(screen.getByRole("heading", { level: 2, name: "Dados do negócio" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2, name: "Tipos e espaços da unidade" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2, name: "Regras comerciais" })).not.toBeInTheDocument();
  });

  it("opens functioning as its own administration module", async () => {
    render(await TenantAdministrationPage({ searchParams: Promise.resolve({ area: "funcionamento" }) }));
    expect(mockedGetReceptionHours).toHaveBeenCalledWith("unit-1");
    expect(mockedGetReceptionHours).toHaveBeenCalledWith("unit-2");
    expect(screen.getAllByRole("button", { name: "Salvar horários" })).toHaveLength(2);
    expect(screen.getAllByLabelText("Segunda abre")[0]).toHaveValue("08:00");
    expect(screen.getAllByLabelText("Segunda fecha")[0]).toHaveValue("18:00");
    expect(screen.queryByRole("heading", { level: 2, name: "Dados do negócio" })).not.toBeInTheDocument();
  });

  it("opens professionals with governed documents and self-onboarding together", async () => {
    render(await TenantAdministrationPage({ searchParams: Promise.resolve({ area: "profissionais" }) }));
    expect(screen.getByText("Termos e políticas do seu negócio")).toBeInTheDocument();
    expect(screen.getByText("O profissional faz o próprio cadastro")).toBeInTheDocument();
    expect(screen.getByText("Profissionais vinculados")).toBeInTheDocument();
    expect(screen.getByText("Cristiana")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2, name: "Dados do negócio" })).not.toBeInTheDocument();
  });

  it("renders existing pricing rules with edit and safe removal controls", async () => {
    vi.mocked(getPricingRules).mockResolvedValue([{
      id: "rule-1", unit_id: "unit-1", resource_category_id: "category-1",
      name: "SALA 01 - HORA", status: "ACTIVE", priority: 100, currency: "BRL",
      rule_definition: { schema_version: 1, modality: "HOURLY", base_price_amount: "39.00", overtime: { hourly_price_amount: "39.00", proportional_until_minutes: 29, full_hour_from_minutes: 30, forgiveness_allowed: false } },
      valid_from: null, valid_until: null,
    }]);
    render(await TenantAdministrationPage({ searchParams: Promise.resolve({ area: "precos" }) }));
    expect(screen.getByText("SALA 01 - HORA")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar regra" })).toBeInTheDocument();
    expect(screen.getByText("Excluir regra de preço")).toBeInTheDocument();
    expect(document.querySelector(".admin-pricing-layout")).toBeInTheDocument();
    expect(document.querySelector(".admin-pricing-record")).toBeInTheDocument();
    expect(document.querySelector(".admin-pricing-editor")).toBeInTheDocument();
    expect(screen.getByText(/Reservas já criadas preservam o snapshot de preço/)).toBeInTheDocument();
  });

  it("renders users as administration content without a legacy product shell", async () => {
    render(await UsersAdminPage({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1, name: "Usuários e acessos" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Configurações" })).toHaveAttribute("href", "/administracao");
    expect(document.querySelector(".tenant-admin-shell")).not.toBeInTheDocument();
  });
  it("shows trusted user identity, role, permissions and protects the owner", async () => {
    vi.mocked(getTenantMemberships).mockResolvedValue([
      { id: "owner-1", tenant_id: "tenant-1", external_user_id: "auth-owner", role: "OWNER", status: "ACTIVE", display_name: "Pessoa Proprietária", email: "owner@example.com" },
      { id: "reception-1", tenant_id: "tenant-1", external_user_id: "auth-reception", role: "RECEPTION", status: "ACTIVE", display_name: "Pessoa Recepção", email: "recepcao@example.com" },
    ]);
    vi.mocked(getTenantMembershipPermissions).mockImplementation(async (id) => id === "owner-1" ? ["DASHBOARD_VIEW","AGENDA_VIEW","AGENDA_MANAGE","AVAILABILITY_VIEW","CHECKIN_MANAGE","FINANCE_VIEW","FINANCE_MANAGE","ADMIN_CONFIG","USER_ADMIN"] : ["DASHBOARD_VIEW","AGENDA_VIEW","AGENDA_MANAGE","AVAILABILITY_VIEW","CHECKIN_MANAGE"]);
    render(await UsersAdminPage({ searchParams: Promise.resolve({}) }));
    expect(screen.getByText("Pessoa Proprietária")).toBeInTheDocument();
    expect(screen.getByText("owner@example.com")).toBeInTheDocument();
    expect(screen.getByText("Pessoa Recepção")).toBeInTheDocument();
    expect(screen.getByText("Acesso integral protegido")).toBeInTheDocument();
    expect(screen.getAllByText("Visualizar agenda").length).toBeGreaterThan(0);
    expect(screen.getByText("Proprietário protegido")).toBeInTheDocument();
    expect(screen.getByText("Bloquear acesso")).toBeInTheDocument();
    expect(screen.getByText("Remover acesso")).toBeInTheDocument();
    expect(screen.getByText("E-mail de acesso")).toBeInTheDocument();
    expect(screen.getByText("Telas e permissões")).toBeInTheDocument();
    expect(screen.getByText("Salvar permissões")).toBeInTheDocument();
    expect(screen.getByText("Dados e papel")).toBeInTheDocument();
    expect(screen.getByText("Controle de acesso")).toBeInTheDocument();
    expect(screen.getByText("Bloquear usuário")).toBeInTheDocument();
    expect(screen.getByText("Remover acesso")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("owner@example.com")).not.toBeInTheDocument();
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
