import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { pricingRuleDefinitionFromForm } from "../app/administracao/pricing-form";

import TenantAdministrationPage from "../app/administracao/page";
import UsersAdminPage from "../app/administracao/usuarios/page";
import RolesPage from "../app/administracao/usuarios/papeis/page";
import {
  getAccessRolePermissionCatalog,
  getAccessRoles,
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

vi.mock("../lib/auth/authorization", () => ({ requireTenantPermission: vi.fn().mockResolvedValue({ permissions: ["USER_VIEW","USER_CREATE","USER_EDIT","USER_BLOCK","USER_DELETE","ROLE_MANAGE","USER_ADMIN"] }) }));

vi.mock("../lib/bcos-api", () => ({
  getAccessRolePermissionCatalog: vi.fn(),
  getAccessRoles: vi.fn(),
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
    vi.mocked(getAccessRoles).mockResolvedValue([]);
    vi.mocked(getPricingRules).mockResolvedValue([]);
    vi.mocked(getProfessionalOnboardingRequests).mockResolvedValue([]);
    vi.mocked(getTenantOnboardingDocuments).mockResolvedValue([]);
    mockedGetReceptionHours.mockImplementation(async (unitId) => unitId === "unit-1"
      ? [{ day_of_week: 0, opens_at: "08:00:00", closes_at: "18:00:00", is_closed: false }]
      : [{ day_of_week: 0, opens_at: "09:00:00", closes_at: "17:00:00", is_closed: false }]);
    vi.mocked(getAccessRoles).mockResolvedValue([{id:"role-reception",tenant_id:"tenant-1",name:"Atendimento",description:"Recepção comercial",active:true,permissions:["AGENDA_VIEW"],assigned_users:1}]);
    vi.mocked(getAccessRolePermissionCatalog).mockResolvedValue([{code:"AGENDA_VIEW",module:"Agenda",action:"Visualizar"},{code:"AGENDA_CREATE",module:"Agenda",action:"Criar"},{code:"FINANCE_VIEW",module:"Financeiro",action:"Visualizar"}]);
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
    expect(screen.getByRole("link", { name: "← Configurações" })).toHaveAttribute("href", "/administracao");
    expect(document.querySelector(".tenant-admin-shell")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Equipe e acessos" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Papéis e permissões" })).toHaveAttribute("href", "/administracao/usuarios/papeis");
    expect(screen.getByText("Gerenciador de acessos do proprietário")).toBeInTheDocument();
    expect(screen.getByText("Sua equipe ainda não possui outros usuários")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Adicionar usuário" })).toHaveAttribute("href", "#adicionar-usuario");
    expect(screen.getByRole("button", { name: "Enviar convite de acesso" })).toBeInTheDocument();
  });
  it("renders roles as a self-explanatory capability configurator", async () => {
    render(await RolesPage());
    expect(screen.getByRole("heading", { level: 1, name: "Papéis e permissões" })).toBeInTheDocument();
    expect(screen.getByText("Seu negócio define os papéis da equipe")).toBeInTheDocument();
    expect(document.querySelector(".role-capability-groups")).toBeInTheDocument();
    expect(document.querySelector(".role-permission-matrix")).not.toBeInTheDocument();
    expect(document.querySelector(".tenant-invite-card-sticky")).not.toBeInTheDocument();
    expect(screen.getAllByLabelText("Agenda: Visualizar")).toHaveLength(2);
    expect(screen.getAllByLabelText("Agenda: Criar")).toHaveLength(2);
    expect(screen.queryByText("—")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "+ Novo papel" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Criar primeiro papel" })).not.toBeInTheDocument();
    expect(screen.getByText("Adicionar papel")).toBeInTheDocument();
    expect(screen.getAllByText("Permitir esta ação em agenda.").length).toBeGreaterThan(0);
  });

  it("shows trusted user identity, role, permissions and protects the owner", async () => {
    vi.mocked(getTenantMemberships).mockResolvedValue([
      { id: "owner-1", tenant_id: "tenant-1", external_user_id: "auth-owner", role: "OWNER", status: "ACTIVE", display_name: "Pessoa Proprietária", email: "owner@example.com" },
      { id: "reception-1", tenant_id: "tenant-1", external_user_id: "auth-reception", role: "RECEPTION", status: "ACTIVE", display_name: "Pessoa Recepção", email: "recepcao@example.com", access_role_id: "role-reception" },
    ]);
    vi.mocked(getTenantMembershipPermissions).mockImplementation(async (id) => id === "owner-1" ? ["DASHBOARD_VIEW","AGENDA_VIEW","AGENDA_MANAGE","AVAILABILITY_VIEW","CHECKIN_MANAGE","FINANCE_VIEW","FINANCE_MANAGE","ADMIN_CONFIG","USER_ADMIN"] : ["DASHBOARD_VIEW","AGENDA_VIEW","AGENDA_MANAGE","AVAILABILITY_VIEW","CHECKIN_MANAGE"]);
    render(await UsersAdminPage({ searchParams: Promise.resolve({}) }));
    expect(screen.getByText("Pessoa Proprietária")).toBeInTheDocument();
    expect(screen.getByText("owner@example.com")).toBeInTheDocument();
    expect(screen.getByText("Pessoa Recepção")).toBeInTheDocument();
    expect(screen.queryByText("Sua equipe ainda não possui outros usuários")).not.toBeInTheDocument();
    expect(screen.getByText("Gerenciador de acessos do proprietário")).toBeInTheDocument();
    expect(screen.getByText("Acesso integral protegido")).toBeInTheDocument();
    expect(screen.getAllByText("Visualizar").length).toBeGreaterThan(0);
    expect(screen.getByText("Proprietário do ambiente")).toBeInTheDocument();
    expect(screen.getAllByText("Remover acesso").length).toBeGreaterThan(0);
    expect(screen.getByText("E-mail de acesso")).toBeInTheDocument();
    expect(screen.getByText("Permissões individuais")).toBeInTheDocument();
    expect(screen.getByText("Salvar permissões individuais")).toBeInTheDocument();
    expect(screen.getByText("Dados e papel")).toBeInTheDocument();
    expect(screen.getByText("Papel cadastrado")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Atendimento")).toBeInTheDocument();
    expect(screen.getByText("Bloqueio e remoção")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Bloquear acesso" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remover acesso" })).toBeInTheDocument();
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
