import "server-only";

import { config as loadEnv } from "dotenv";
import path from "node:path";

loadEnv({
  path: path.resolve(process.cwd(), "..", "..", ".env.local"),
  override: false,
});

export type Unit = { id: string; name: string; timezone: string; active: boolean; created_at: string; updated_at: string };
export type Resource = { id: string; unit_id: string; category_id: string; name: string; operational_status: string; buffer_before_minutes: number; buffer_after_minutes: number; active: boolean };
export type Professional = { id: string; external_user_id: string | null; name: string; email: string | null; phone: string | null; status: string };
export type Booking = { id: string; unit_id: string; resource_id: string; professional_id: string; series_id: string | null; status: string; starts_at: string; ends_at: string; buffer_before_minutes: number; buffer_after_minutes: number; pricing_snapshot: Record<string, unknown> };
export type Usage = { id: string; booking_id: string; resource_id: string; professional_id: string; status: string; checked_in_at: string | null; checked_out_at: string | null };
export type AvailabilityItem = { resource_id: string; available: boolean; reason: string | null };
export type AvailabilityResponse = { starts_at: string; ends_at: string; resources: AvailabilityItem[] };
export type Invoice = { id: string; professional_id: string; source_usage_id: string | null; professional_billing_contract_id: string | null; billing_cycle_start: string | null; billing_cycle_end: string | null; manual_closed_at: string | null; status: string; currency: string; subtotal_amount: string; discount_amount: string; total_amount: string; created_at: string; updated_at: string };
export type InvoiceItem = { id: string; usage_id: string | null; item_type: string; description: string; quantity: string; unit_amount: string; total_amount: string; billing_period_start: string | null; billing_period_end: string | null; related_invoice_item_id: string | null; created_at: string };
export type InvoiceDetail = Invoice & { items: InvoiceItem[]; confirmed_amount: string; remaining_amount: string };
export type Payment = { id: string; invoice_id: string; idempotency_key: string; method: string; status: string; currency: string; amount: string; reference: string | null; metadata: Record<string, unknown>; paid_at: string | null; created_at: string; updated_at: string };
export type PaymentResult = { payment: Payment; invoice_status: string; invoice_total_amount: string; confirmed_amount: string; remaining_amount: string };

const API_BASE_URL = process.env.BCOS_API_BASE_URL ?? "http://127.0.0.1:8010";

function getRequiredEnvironment() {
  const token = process.env.BCOS_HOMOLOGATION_BEARER_TOKEN;
  const tenantId = process.env.BCOS_HUMAN_TENANT_ID;
  if (!token) throw new Error("BCOS_HOMOLOGATION_BEARER_TOKEN não está disponível no servidor Next.js.");
  if (!tenantId) throw new Error("BCOS_HUMAN_TENANT_ID não está disponível no servidor Next.js.");
  return { token, tenantId };
}

async function apiRequest<T>(pathName: string, init: RequestInit = {}): Promise<T> {
  const { token, tenantId } = getRequiredEnvironment();
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
  return (await response.json()) as T;
}

async function apiGet<T>(pathName: string): Promise<T> { return apiRequest<T>(pathName, { method: "GET" }); }
async function apiPost<T>(pathName: string, body?: Record<string, unknown>): Promise<T> {
  return apiRequest<T>(pathName, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
}

export async function getUnits(): Promise<Unit[]> { return apiGet<Unit[]>("/api/v1/units"); }
export async function getResources(unitId?: string): Promise<Resource[]> {
  const search = new URLSearchParams();
  if (unitId) search.set("unit_id", unitId);
  const query = search.toString();
  return apiGet<Resource[]>(`/api/v1/resources${query ? `?${query}` : ""}`);
}
export async function getProfessionals(): Promise<Professional[]> { return apiGet<Professional[]>("/api/v1/professionals"); }

export async function getBookings(params?: { startsFrom?: string; startsUntil?: string; professionalId?: string; resourceId?: string; status?: string }): Promise<Booking[]> {
  const search = new URLSearchParams();
  if (params?.startsFrom) search.set("starts_from", params.startsFrom);
  if (params?.startsUntil) search.set("starts_until", params.startsUntil);
  if (params?.professionalId) search.set("professional_id", params.professionalId);
  if (params?.resourceId) search.set("resource_id", params.resourceId);
  if (params?.status) search.set("status", params.status);
  const query = search.toString();
  return apiGet<Booking[]>(`/api/v1/bookings${query ? `?${query}` : ""}`);
}

export async function getAvailability(input: { unitId: string; startsAt: string; endsAt: string; resourceId?: string }): Promise<AvailabilityResponse> {
  const search = new URLSearchParams({ unit_id: input.unitId, starts_at: input.startsAt, ends_at: input.endsAt });
  if (input.resourceId) search.set("resource_id", input.resourceId);
  return apiGet<AvailabilityResponse>(`/api/v1/availability?${search.toString()}`);
}

export async function createBooking(input: { unitId: string; resourceId: string; professionalId: string; startsAt: string; endsAt: string; notes?: string }): Promise<Booking> {
  return apiPost<Booking>("/api/v1/bookings", {
    unit_id: input.unitId,
    resource_id: input.resourceId,
    professional_id: input.professionalId,
    starts_at: input.startsAt,
    ends_at: input.endsAt,
    ...(input.notes ? { notes: input.notes } : {}),
  });
}

export async function confirmBooking(bookingId: string): Promise<Booking> {
  return apiPost<Booking>(`/api/v1/bookings/${encodeURIComponent(bookingId)}/confirm`);
}

export async function checkInBooking(bookingId: string, checkedInAt?: string): Promise<Usage> {
  return apiPost<Usage>("/api/v1/usages/check-in", { booking_id: bookingId, ...(checkedInAt ? { checked_in_at: checkedInAt } : {}) });
}
export async function checkOutUsage(usageId: string, checkedOutAt?: string): Promise<Usage> {
  return apiPost<Usage>(`/api/v1/usages/${encodeURIComponent(usageId)}/check-out`, checkedOutAt ? { checked_out_at: checkedOutAt } : {});
}
export async function getInvoices(params?: { professionalId?: string; status?: string; limit?: number; offset?: number }): Promise<Invoice[]> {
  const search = new URLSearchParams();
  if (params?.professionalId) search.set("professional_id", params.professionalId);
  if (params?.status) search.set("status", params.status);
  if (params?.limit !== undefined) search.set("limit", String(params.limit));
  if (params?.offset !== undefined) search.set("offset", String(params.offset));
  const query = search.toString();
  return apiGet<Invoice[]>(`/api/v1/invoices${query ? `?${query}` : ""}`);
}
export async function getInvoice(invoiceId: string): Promise<InvoiceDetail> { return apiGet<InvoiceDetail>(`/api/v1/invoices/${encodeURIComponent(invoiceId)}`); }
export async function closeManualInvoice(invoiceId: string): Promise<Invoice> { return apiPost<Invoice>(`/api/v1/invoices/${encodeURIComponent(invoiceId)}/close`); }
export async function confirmPixPayment(input: { invoiceId: string; idempotencyKey: string; amount: string; reference?: string; paidAt?: string }): Promise<PaymentResult> {
  return apiPost<PaymentResult>("/api/v1/payments/pix/confirm", {
    invoice_id: input.invoiceId,
    idempotency_key: input.idempotencyKey,
    amount: input.amount,
    ...(input.reference ? { reference: input.reference } : {}),
    ...(input.paidAt ? { paid_at: input.paidAt } : {}),
  });
}
