import "server-only";

import { config as loadEnv } from "dotenv";
import path from "node:path";
import { cookies } from "next/headers";

import { auth } from "./auth/server";

loadEnv({ path: path.resolve(process.cwd(), "..", "..", ".env.local"), override: false });

export type Unit = { id: string; name: string; timezone: string; active: boolean; created_at: string; updated_at: string };
export type ResourceCategory = { id: string; name: string; active: boolean };
export type PricingRule = { id: string; unit_id: string | null; resource_category_id: string | null; name: string; status: string; priority: number; currency: "BRL"; rule_definition: Record<string, unknown>; valid_from: string | null; valid_until: string | null };
export type Resource = { id: string; unit_id: string; category_id: string; name: string; operational_status: string; buffer_before_minutes: number; buffer_after_minutes: number; active: boolean };
export type Professional = { id: string; external_user_id: string | null; name: string; email: string | null; phone: string | null; profession: string | null; council_type: string | null; council_number: string | null; status: string };
export type Booking = { id: string; unit_id: string; resource_id: string; professional_id: string; series_id: string | null; status: string; starts_at: string; ends_at: string; buffer_before_minutes: number; buffer_after_minutes: number; pricing_snapshot: Record<string, unknown> };
export type Usage = { id: string; booking_id: string; resource_id: string; professional_id: string; status: string; checked_in_at: string | null; checked_out_at: string | null };
export type ReceptionResourceState = { resource_id: string; resource_name: string; operational_status: string; booking_id: string | null; professional_id: string | null; starts_at: string | null; ends_at: string | null; usage_id: string | null; usage_status: string | null; checked_in_at: string | null; checked_out_at: string | null };
export type ReceptionNow = { unit_id: string; generated_at: string; resources: ReceptionResourceState[] };
export type AgendaEntry = { booking: Booking; usage: Usage | null };
export type AvailabilityItem = { resource_id: string; available: boolean; reason: string | null };
export type AvailabilityResponse = { starts_at: string; ends_at: string; resources: AvailabilityItem[] };
export type ProfessionalCommercialOption = { resource_id: string; resource_name: string; resource_category_id: string; available: boolean; unavailable_reason: string | null; pricing_snapshot: Record<string, unknown> | null; price_amount: string | null; price_currency: string | null; price_modality: string | null };
export type ProfessionalCommercialAvailability = { unit_id: string; starts_at: string; ends_at: string; resources: ProfessionalCommercialOption[] };
export type Invoice = { id: string; professional_id: string; source_usage_id: string | null; professional_billing_contract_id: string | null; billing_cycle_start: string | null; billing_cycle_end: string | null; manual_closed_at: string | null; status: string; currency: string; subtotal_amount: string; discount_amount: string; total_amount: string; created_at: string; updated_at: string };
export type InvoiceItem = { id: string; usage_id: string | null; item_type: string; description: string; quantity: string; unit_amount: string; total_amount: string; billing_period_start: string | null; billing_period_end: string | null; related_invoice_item_id: string | null; created_at: string };
export type InvoiceDetail = Invoice & { items: InvoiceItem[]; confirmed_amount: string; remaining_amount: string };
export type Payment = { id: string; invoice_id: string; idempotency_key: string; method: string; status: string; currency: string; amount: string; reference: string | null; metadata: Record<string, unknown>; paid_at: string | null; created_at: string; updated_at: string };
export type ContractingTenant = { id: string; name: string; slug: string; status: "PENDING_ACTIVATION" | "ACTIVE" | "SUSPENDED" | "INACTIVE"; legal_name: string; trade_name: string; tax_id: string | null; email: string; phone: string | null; owner_external_user_id: string | null; owner_membership_status: "INVITED" | "ACTIVE" | "INACTIVE" | null; created_at: string };
export type ContractingTenantCreate = { name: string; slug: string; legalName: string; tradeName: string; taxId?: string; email: string; phone?: string; ownerEmail?: string };
export type TenantMembership = { id: string; tenant_id: string; external_user_id: string; role: "OWNER" | "ADMIN" | "RECEPTION" | "PROFESSIONAL"; status: "INVITED" | "ACTIVE" | "INACTIVE"; display_name: string | null; email: string | null };
export type TenantMembershipInvite = { displayName: string; email: string; role: "ADMIN" | "RECEPTION" | "PROFESSIONAL" };
export type AccessTenant = { tenant_id: string; tenant_name: string; role: "OWNER" | "ADMIN" | "RECEPTION" | "PROFESSIONAL"; destination: "/administracao" | "/" | "/profissional" };
export type AccessResolution = { platform_destination: "/platform" | null; tenants: AccessTenant[] };
export type PendingInvitation = TenantMembership;
export type PublicProfessionalOnboarding = { tenant_name: string; documents: Array<{ id: string; document_type: string; version: string; title: string; content: string }> };
export type ProfessionalOnboardingRequest = { id: string; tenant_id: string; tenant_name: string; name: string; email: string; phone: string | null; profession: string | null; council_type: string | null; council_number: string | null; status: string; created_at: string };
export type ManagedOnboardingDocument = { id: string; tenant_id: string | null; document_type: "PROFESSIONAL_TERMS" | "UNIT_POLICY" | "RESERVATION_POLICY" | "FINANCIAL_POLICY" | "OTHER"; version: string; title: string; content: string; status: string; effective_at: string };
export type ProfessionalOnboardingLink = { id: string; public_slug: string; public_path: string };

export async function getPublicProfessionalOnboarding(slug: string): Promise<PublicProfessionalOnboarding> {
  return publicApiRequest<PublicProfessionalOnboarding>(`/api/v1/professional-onboarding/public/${encodeURIComponent(slug)}`);
}

export async function submitPublicProfessionalOnboarding(slug: string, payload: Record<string, unknown>): Promise<ProfessionalOnboardingRequest> {
  return publicApiPost<ProfessionalOnboardingRequest>(`/api/v1/professional-onboarding/public/${encodeURIComponent(slug)}`, payload);
}

export async function getTenantOnboardingDocuments(): Promise<ManagedOnboardingDocument[]> {
  return apiGet<ManagedOnboardingDocument[]>("/api/v1/professional-onboarding/documents");
}
export async function publishTenantOnboardingDocument(input: { document_type: ManagedOnboardingDocument["document_type"]; version: string; title: string; content: string }): Promise<ManagedOnboardingDocument> {
  return apiPut<ManagedOnboardingDocument>("/api/v1/professional-onboarding/documents", input);
}

export async function createProfessionalOnboardingLink(): Promise<ProfessionalOnboardingLink> {
  return apiPost<ProfessionalOnboardingLink>("/api/v1/professional-onboarding/links", {});
}

export async function getProfessionalOnboardingRequests(): Promise<ProfessionalOnboardingRequest[]> {
  return apiRequest<ProfessionalOnboardingRequest[]>("/api/v1/professional-onboarding/requests");
}

export async function approveProfessionalOnboardingRequest(requestId: string): Promise<ProfessionalOnboardingRequest> {
  return apiPost<ProfessionalOnboardingRequest>(`/api/v1/professional-onboarding/requests/${encodeURIComponent(requestId)}/approve`, {});
}

export type ProfessionalAccessInvitation = { id: string; tenant_id: string; tenant_name: string; professional_id: string; professional_name: string; email: string; status: string; expires_at: string };
export type ProfessionalAccessInvitationCreated = { id: string; professional_id: string; email: string; status: string; expires_at: string };
export type TenantProfile = { legal_name: string; trade_name: string; tax_id: string | null; email: string; phone: string | null };
export type ReceptionHour = { day_of_week: number; opens_at: string | null; closes_at: string | null; is_closed: boolean };

export type PaymentResult = { payment: Payment; invoice_status: string; invoice_total_amount: string; confirmed_amount: string; remaining_amount: string };

const API_BASE_URL = process.env.BCOS_API_BASE_URL ?? "http://127.0.0.1:8010";

async function getBearerToken(): Promise<string> {
  if (process.env.BCOS_IDENTITY_PROVIDER === "neon") {
    const { data, error } = await auth.token();
    if (error || !data?.token) {
      throw new Error("Sessão Neon Auth autenticada é obrigatória para acessar a BCOS API.");
    }
    return data.token;
  }

  const token = process.env.BCOS_HOMOLOGATION_BEARER_TOKEN;
  if (!token) throw new Error("BCOS_HOMOLOGATION_BEARER_TOKEN não está disponível no servidor Next.js.");
  return token;
}

const TENANT_COOKIE = "bcos_tenant_id";

async function getTenantId(): Promise<string> {
  if (process.env.BCOS_IDENTITY_PROVIDER === "neon") {
    const access = await getAccessResolution();
    const cookieStore = await cookies();
    const selectedId = cookieStore.get(TENANT_COOKIE)?.value;
    const selected = selectedId
      ? access.tenants.find((tenant) => tenant.tenant_id === selectedId)
      : undefined;
    if (selected) return selected.tenant_id;
    if (access.tenants.length === 1) return access.tenants[0].tenant_id;
    throw new Error("Selecione um coworking autorizado antes de acessar dados do tenant.");
  }

  const tenantId = process.env.BCOS_HUMAN_TENANT_ID;
  if (!tenantId) throw new Error("BCOS_HUMAN_TENANT_ID não está disponível no ambiente de homologação.");
  return tenantId;
}

async function apiRequest<T>(pathName: string, init: RequestInit = {}): Promise<T> {
  const token = await getBearerToken();
  const tenantId = await getTenantId();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("X-Tenant-Id", tenantId);
  headers.set("Accept", "application/json");
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE_URL}${pathName}`, { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`BCOS API ${init.method ?? "GET"} ${pathName} falhou com HTTP ${response.status}: ${body}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function publicApiRequest<T>(pathName: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE_URL}${pathName}`, { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`BCOS Public API ${init.method ?? "GET"} ${pathName} falhou com HTTP ${response.status}: ${body}`);
  }
  return (await response.json()) as T;
}

async function publicApiPost<T>(pathName: string, body: Record<string, unknown>): Promise<T> {
  return publicApiRequest<T>(pathName, { method: "POST", body: JSON.stringify(body) });
}

async function identityApiRequest<T>(pathName: string, init: RequestInit = {}): Promise<T> {
  const token = await getBearerToken();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("Accept", "application/json");
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE_URL}${pathName}`, { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`BCOS Identity API ${init.method ?? "GET"} ${pathName} falhou com HTTP ${response.status}: ${body}`);
  }
  return (await response.json()) as T;
}

export async function getAccessResolution(): Promise<AccessResolution> {
  return identityApiRequest<AccessResolution>("/api/v1/access");
}

export async function persistSelectedTenant(tenantId: string): Promise<AccessTenant> {
  const access = await getAccessResolution();
  const selected = access.tenants.find((tenant) => tenant.tenant_id === tenantId);
  if (!selected) throw new Error("Tenant selecionado não está autorizado para esta identidade.");

  const cookieStore = await cookies();
  cookieStore.set(TENANT_COOKIE, selected.tenant_id, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
  });
  return selected;
}

export async function getPendingProfessionalInvitations(): Promise<ProfessionalAccessInvitation[]> {
  return identityApiRequest<ProfessionalAccessInvitation[]>("/api/v1/professional-invitations");
}

export async function acceptProfessionalInvitation(invitationId: string): Promise<ProfessionalAccessInvitation> {
  return identityApiRequest<ProfessionalAccessInvitation>(`/api/v1/professional-invitations/${encodeURIComponent(invitationId)}/accept`, { method: "POST" });
}

export async function getPendingInvitations(): Promise<PendingInvitation[]> {
  return identityApiRequest<PendingInvitation[]>("/api/v1/invitations");
}

export async function acceptInvitation(membershipId: string): Promise<TenantMembership> {
  return identityApiRequest<TenantMembership>(`/api/v1/invitations/${encodeURIComponent(membershipId)}/accept`, { method: "POST" });
}

async function platformApiRequest<T>(pathName: string, init: RequestInit = {}): Promise<T> {
  const token = await getBearerToken();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("Accept", "application/json");
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE_URL}${pathName}`, { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`BCOS Platform API ${init.method ?? "GET"} ${pathName} falhou com HTTP ${response.status}: ${body}`);
  }
  return (await response.json()) as T;
}

async function apiGet<T>(pathName: string): Promise<T> { return apiRequest<T>(pathName, { method: "GET" }); }
async function apiPost<T>(pathName: string, body?: Record<string, unknown>): Promise<T> { return apiRequest<T>(pathName, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }); }
async function apiPut<T>(pathName: string, body: unknown): Promise<T> { return apiRequest<T>(pathName, { method: "PUT", body: JSON.stringify(body) }); }
async function apiPatch<T>(pathName: string, body: unknown): Promise<T> { return apiRequest<T>(pathName, { method: "PATCH", body: JSON.stringify(body) }); }

export async function getTenantProfile(): Promise<TenantProfile> { return apiGet<TenantProfile>("/api/v1/admin/profile"); }
export async function updateTenantProfile(input: TenantProfile): Promise<TenantProfile> { return apiPut<TenantProfile>("/api/v1/admin/profile", input); }
export async function getUnits(): Promise<Unit[]> { return apiGet<Unit[]>("/api/v1/units"); }
export async function createUnit(input: { name: string; timezone: string }): Promise<Unit> { return apiPost<Unit>("/api/v1/units", { name: input.name, timezone: input.timezone, active: true }); }
export async function updateUnit(unitId: string, input: { name: string; timezone: string; active: boolean }): Promise<Unit> { return apiPatch<Unit>(`/api/v1/units/${encodeURIComponent(unitId)}`, input); }
export async function deleteUnit(unitId: string): Promise<void> { return apiRequest<void>(`/api/v1/units/${encodeURIComponent(unitId)}`, { method: "DELETE" }); }
export async function getReceptionHours(unitId: string): Promise<ReceptionHour[]> { return apiGet<ReceptionHour[]>(`/api/v1/units/${encodeURIComponent(unitId)}/reception-hours`); }
export async function updateReceptionHours(unitId: string, hours: ReceptionHour[]): Promise<ReceptionHour[]> { return apiPut<ReceptionHour[]>(`/api/v1/units/${encodeURIComponent(unitId)}/reception-hours`, hours); }
export async function getResourceCategories(): Promise<ResourceCategory[]> { return apiGet<ResourceCategory[]>("/api/v1/resource-categories"); }
export async function createResourceCategory(input: { name: string }): Promise<ResourceCategory> { return apiPost<ResourceCategory>("/api/v1/resource-categories", { name: input.name, active: true }); }
export async function updateResourceCategory(categoryId: string, input: { name: string; active: boolean }): Promise<ResourceCategory> { return apiPatch<ResourceCategory>(`/api/v1/resource-categories/${encodeURIComponent(categoryId)}`, input); }
export async function deleteResourceCategory(categoryId: string): Promise<void> { return apiRequest<void>(`/api/v1/resource-categories/${encodeURIComponent(categoryId)}`, { method: "DELETE" }); }
export async function getResources(unitId?: string): Promise<Resource[]> { const search = new URLSearchParams(); if (unitId) search.set("unit_id", unitId); const query = search.toString(); return apiGet<Resource[]>(`/api/v1/resources${query ? `?${query}` : ""}`); }
export async function createProfessionalAccessInvitation(professionalId: string): Promise<ProfessionalAccessInvitationCreated> { return apiPost<ProfessionalAccessInvitationCreated>(`/api/v1/professional-invitations/professionals/${encodeURIComponent(professionalId)}`, {}); }
export async function getProfessionals(): Promise<Professional[]> { return apiGet<Professional[]>("/api/v1/professionals"); }
export async function createProfessional(input: { name: string; email?: string; phone?: string; profession?: string; councilType?: string; councilNumber?: string }): Promise<Professional> { return apiPost<Professional>("/api/v1/professionals", { name: input.name, ...(input.email ? { email: input.email } : {}), ...(input.phone ? { phone: input.phone } : {}), ...(input.profession ? { profession: input.profession } : {}), ...(input.councilType ? { council_type: input.councilType } : {}), ...(input.councilNumber ? { council_number: input.councilNumber } : {}) }); }
export async function updateProfessional(professionalId: string, input: { name: string; email: string | null; phone: string | null; profession: string | null; council_type: string | null; council_number: string | null; status: string }): Promise<Professional> { return apiPatch<Professional>(`/api/v1/professionals/${encodeURIComponent(professionalId)}`, input); }
export async function createResource(input: { unitId: string; categoryId: string; name: string }): Promise<Resource> { return apiPost<Resource>("/api/v1/resources", { unit_id: input.unitId, category_id: input.categoryId, name: input.name, buffer_before_minutes: 0, buffer_after_minutes: 0, active: true }); }
export async function updateResource(resourceId: string, input: { name: string; operational_status: string; buffer_before_minutes: number; buffer_after_minutes: number; active: boolean }): Promise<Resource> { return apiPatch<Resource>(`/api/v1/resources/${encodeURIComponent(resourceId)}`, input); }
export async function deleteResource(resourceId: string): Promise<void> { return apiRequest<void>(`/api/v1/resources/${encodeURIComponent(resourceId)}`, { method: "DELETE" }); }
export async function getPricingRules(): Promise<PricingRule[]> { return apiGet<PricingRule[]>("/api/v1/pricing-rules"); }
export async function createPricingRule(input: { name: string; unitId?: string; categoryId?: string; priority: number; ruleDefinition: Record<string, unknown>; validFrom?: string; validUntil?: string }): Promise<PricingRule> { return apiPost<PricingRule>("/api/v1/pricing-rules", { name: input.name, ...(input.unitId ? { unit_id: input.unitId } : {}), ...(input.categoryId ? { resource_category_id: input.categoryId } : {}), priority: input.priority, currency: "BRL", rule_definition: input.ruleDefinition, ...(input.validFrom ? { valid_from: input.validFrom } : {}), ...(input.validUntil ? { valid_until: input.validUntil } : {}) }); }
export async function updatePricingRule(ruleId: string, input: { name: string; unitId?: string; categoryId?: string; status: string; priority: number; ruleDefinition: Record<string, unknown>; validFrom?: string; validUntil?: string }): Promise<PricingRule> { return apiPatch<PricingRule>(`/api/v1/pricing-rules/${encodeURIComponent(ruleId)}`, { name: input.name, unit_id: input.unitId || null, resource_category_id: input.categoryId || null, status: input.status, priority: input.priority, currency: "BRL", rule_definition: input.ruleDefinition, valid_from: input.validFrom || null, valid_until: input.validUntil || null }); }
export async function deletePricingRule(ruleId: string): Promise<void> { return apiRequest<void>(`/api/v1/pricing-rules/${encodeURIComponent(ruleId)}`, { method: "DELETE" }); }
export async function getReceptionNow(unitId: string): Promise<ReceptionNow> { return apiGet<ReceptionNow>(`/api/v1/reception/now?${new URLSearchParams({ unit_id: unitId }).toString()}`); }
export async function getReceptionAgenda(input: { unitId: string; startsAt: string; endsAt: string }): Promise<AgendaEntry[]> { return apiGet<AgendaEntry[]>(`/api/v1/reception/agenda?${new URLSearchParams({ unit_id: input.unitId, starts_at: input.startsAt, ends_at: input.endsAt }).toString()}`); }
export async function getBookings(params?: { startsFrom?: string; startsUntil?: string; professionalId?: string; resourceId?: string; status?: string }): Promise<Booking[]> { const search = new URLSearchParams(); if (params?.startsFrom) search.set("starts_from", params.startsFrom); if (params?.startsUntil) search.set("starts_until", params.startsUntil); if (params?.professionalId) search.set("professional_id", params.professionalId); if (params?.resourceId) search.set("resource_id", params.resourceId); if (params?.status) search.set("status", params.status); const query = search.toString(); return apiGet<Booking[]>(`/api/v1/bookings${query ? `?${query}` : ""}`); }
export async function getAvailability(input: { unitId: string; startsAt: string; endsAt: string; resourceId?: string }): Promise<AvailabilityResponse> { const search = new URLSearchParams({ unit_id: input.unitId, starts_at: input.startsAt, ends_at: input.endsAt }); if (input.resourceId) search.set("resource_id", input.resourceId); return apiGet<AvailabilityResponse>(`/api/v1/availability?${search.toString()}`); }
export async function createBooking(input: { unitId: string; resourceId: string; professionalId: string; startsAt: string; endsAt: string; notes?: string }): Promise<Booking> { return apiPost<Booking>("/api/v1/bookings", { unit_id: input.unitId, resource_id: input.resourceId, professional_id: input.professionalId, starts_at: input.startsAt, ends_at: input.endsAt, ...(input.notes ? { notes: input.notes } : {}) }); }
export async function confirmBooking(bookingId: string): Promise<Booking> { return apiPost<Booking>(`/api/v1/bookings/${encodeURIComponent(bookingId)}/confirm`); }
export async function checkInBooking(bookingId: string, checkedInAt?: string): Promise<Usage> { return apiPost<Usage>("/api/v1/usages/check-in", { booking_id: bookingId, ...(checkedInAt ? { checked_in_at: checkedInAt } : {}) }); }
export async function checkOutUsage(usageId: string, checkedOutAt?: string): Promise<Usage> { return apiPost<Usage>(`/api/v1/usages/${encodeURIComponent(usageId)}/check-out`, checkedOutAt ? { checked_out_at: checkedOutAt } : {}); }
export async function getInvoices(params?: { professionalId?: string; status?: string; limit?: number; offset?: number }): Promise<Invoice[]> { const search = new URLSearchParams(); if (params?.professionalId) search.set("professional_id", params.professionalId); if (params?.status) search.set("status", params.status); if (params?.limit !== undefined) search.set("limit", String(params.limit)); if (params?.offset !== undefined) search.set("offset", String(params.offset)); const query = search.toString(); return apiGet<Invoice[]>(`/api/v1/invoices${query ? `?${query}` : ""}`); }
export async function getInvoice(invoiceId: string): Promise<InvoiceDetail> { return apiGet<InvoiceDetail>(`/api/v1/invoices/${encodeURIComponent(invoiceId)}`); }
export async function closeManualInvoice(invoiceId: string): Promise<Invoice> { return apiPost<Invoice>(`/api/v1/invoices/${encodeURIComponent(invoiceId)}/close`); }
export async function confirmPixPayment(input: { invoiceId: string; idempotencyKey: string; amount: string; reference?: string; paidAt?: string }): Promise<PaymentResult> { return apiPost<PaymentResult>("/api/v1/payments/pix/confirm", { invoice_id: input.invoiceId, idempotency_key: input.idempotencyKey, amount: input.amount, ...(input.reference ? { reference: input.reference } : {}), ...(input.paidAt ? { paid_at: input.paidAt } : {}) }); }
export async function getMyBookings(): Promise<Booking[]> { return apiGet<Booking[]>("/api/v1/professional/me/bookings"); }
export async function getMyCommercialAvailability(input: { unitId: string; startsAt: string; endsAt: string; categoryId?: string }): Promise<ProfessionalCommercialAvailability> { const search = new URLSearchParams({ unit_id: input.unitId, starts_at: input.startsAt, ends_at: input.endsAt }); if (input.categoryId) search.set("category_id", input.categoryId); return apiGet<ProfessionalCommercialAvailability>(`/api/v1/professional/me/commercial-availability?${search.toString()}`); }
export async function createMyBooking(input: { unitId: string; resourceId: string; startsAt: string; endsAt: string; notes?: string }): Promise<Booking> { return apiPost<Booking>("/api/v1/professional/me/bookings", { unit_id: input.unitId, resource_id: input.resourceId, starts_at: input.startsAt, ends_at: input.endsAt, ...(input.notes ? { notes: input.notes } : {}) }); }
export async function getMyInvoices(): Promise<Invoice[]> { return apiGet<Invoice[]>("/api/v1/professional/me/invoices"); }

export async function createContractingTenant(input: ContractingTenantCreate): Promise<ContractingTenant> {
  return platformApiRequest<ContractingTenant>("/api/v1/platform/tenants", {
    method: "POST",
    body: JSON.stringify({
      name: input.name,
      slug: input.slug,
      legal_name: input.legalName,
      trade_name: input.tradeName,
      tax_id: input.taxId || null,
      email: input.email,
      phone: input.phone || null,
      ...(input.ownerEmail ? { owner_email: input.ownerEmail } : {}),
    }),
  });
}

export async function getContractingTenants(): Promise<ContractingTenant[]> {
  return platformApiRequest<ContractingTenant[]>("/api/v1/platform/tenants");
}

export async function getContractingTenant(tenantId: string): Promise<ContractingTenant> {
  return platformApiRequest<ContractingTenant>(`/api/v1/platform/tenants/${encodeURIComponent(tenantId)}`);
}

export async function updateContractingTenantStatus(
  tenantId: string,
  status: ContractingTenant["status"],
): Promise<ContractingTenant> {
  return platformApiRequest<ContractingTenant>(
    `/api/v1/platform/tenants/${encodeURIComponent(tenantId)}/status`,
    { method: "PATCH", body: JSON.stringify({ status }) },
  );
}


export async function getTenantMemberships(): Promise<TenantMembership[]> {
  return apiGet<TenantMembership[]>("/api/v1/admin/memberships");
}

export async function inviteTenantMembership(input: TenantMembershipInvite): Promise<void> {
  await apiPost("/api/v1/admin/memberships/invitations", { display_name: input.displayName, email: input.email, role: input.role });
}

export async function updateTenantMembershipStatus(
  membershipId: string,
  status: "ACTIVE" | "INACTIVE",
): Promise<TenantMembership> {
  return apiRequest<TenantMembership>(
    `/api/v1/admin/memberships/${encodeURIComponent(membershipId)}/status`,
    { method: "PATCH", body: JSON.stringify({ status }) },
  );
}


export async function updateTenantMembership(
  membershipId: string,
  input: { display_name: string; email: string | null; role: "ADMIN" | "RECEPTION" | "PROFESSIONAL" },
): Promise<TenantMembership> {
  return apiPatch<TenantMembership>(`/api/v1/admin/memberships/${encodeURIComponent(membershipId)}`, input);
}

export async function removeTenantMembership(membershipId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/admin/memberships/${encodeURIComponent(membershipId)}`, { method: "DELETE" });
}

export async function inviteContractingTenantOwner(tenantId: string, email: string): Promise<{ membership_id: string; tenant_id: string; external_user_id: string; role: string; status: string }> {
  return platformApiRequest(`/api/v1/platform/tenants/${encodeURIComponent(tenantId)}/owner-invitations`, {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}
