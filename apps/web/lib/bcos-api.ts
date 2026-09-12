import "server-only";

import { config as loadEnv } from "dotenv";
import path from "node:path";

loadEnv({
  path: path.resolve(process.cwd(), "..", "..", ".env.local"),
  override: false,
});

export type Unit = {
  id: string;
  name: string;
  timezone: string;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type Resource = {
  id: string;
  unit_id: string;
  category_id: string;
  name: string;
  operational_status: string;
  buffer_before_minutes: number;
  buffer_after_minutes: number;
  active: boolean;
};

export type Professional = {
  id: string;
  external_user_id: string | null;
  name: string;
  email: string | null;
  phone: string | null;
  status: string;
};

export type Booking = {
  id: string;
  unit_id: string;
  resource_id: string;
  professional_id: string;
  series_id: string | null;
  status: string;
  starts_at: string;
  ends_at: string;
  buffer_before_minutes: number;
  buffer_after_minutes: number;
  pricing_snapshot: Record<string, unknown>;
};

const API_BASE_URL = "http://127.0.0.1:8010";

function getRequiredEnvironment() {
  const token = process.env.BCOS_HOMOLOGATION_BEARER_TOKEN;
  const tenantId = process.env.BCOS_HUMAN_TENANT_ID;

  if (!token) {
    throw new Error(
      "BCOS_HOMOLOGATION_BEARER_TOKEN não está disponível no servidor Next.js.",
    );
  }

  if (!tenantId) {
    throw new Error(
      "BCOS_HUMAN_TENANT_ID não está disponível no servidor Next.js.",
    );
  }

  return {
    token,
    tenantId,
  };
}

async function apiGet<T>(pathName: string): Promise<T> {
  const { token, tenantId } = getRequiredEnvironment();

  const response = await fetch(`${API_BASE_URL}${pathName}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Tenant-Id": tenantId,
      Accept: "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const body = await response.text();

    throw new Error(
      `BCOS API GET ${pathName} falhou com HTTP ${response.status}: ${body}`,
    );
  }

  return (await response.json()) as T;
}

export async function getUnits(): Promise<Unit[]> {
  return apiGet<Unit[]>("/api/v1/units");
}

export async function getResources(
  unitId?: string,
): Promise<Resource[]> {
  const search = new URLSearchParams();

  if (unitId) {
    search.set("unit_id", unitId);
  }

  const query = search.toString();

  return apiGet<Resource[]>(
    `/api/v1/resources${query ? `?${query}` : ""}`,
  );
}

export async function getProfessionals(): Promise<Professional[]> {
  return apiGet<Professional[]>("/api/v1/professionals");
}

export async function getBookings(params?: {
  startsFrom?: string;
  startsUntil?: string;
  professionalId?: string;
  resourceId?: string;
  status?: string;
}): Promise<Booking[]> {
  const search = new URLSearchParams();

  if (params?.startsFrom) {
    search.set("starts_from", params.startsFrom);
  }

  if (params?.startsUntil) {
    search.set("starts_until", params.startsUntil);
  }

  if (params?.professionalId) {
    search.set("professional_id", params.professionalId);
  }

  if (params?.resourceId) {
    search.set("resource_id", params.resourceId);
  }

  if (params?.status) {
    search.set("status", params.status);
  }

  const query = search.toString();

  return apiGet<Booking[]>(
    `/api/v1/bookings${query ? `?${query}` : ""}`,
  );
}