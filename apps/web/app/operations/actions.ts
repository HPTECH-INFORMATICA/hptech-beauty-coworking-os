"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  checkInBooking,
  checkOutUsage,
  closeManualInvoice,
  confirmBooking,
  confirmPixPayment,
  createBooking,
  getAvailability,
} from "../../lib/bcos-api";

function required(formData: FormData, name: string): string {
  const value = formData.get(name);
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Campo obrigatório ausente: ${name}`);
  }
  return value.trim();
}

function optional(formData: FormData, name: string): string | undefined {
  const value = formData.get(name);
  return typeof value === "string" && value.trim() !== "" ? value.trim() : undefined;
}

function localDateTimeInZoneToIso(value: string, timeZone: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
  if (!match) throw new Error("Data e hora inválidas.");

  const [, year, month, day, hour, minute] = match;
  const wanted = Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute));
  let instant = wanted;
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });

  for (let attempt = 0; attempt < 2; attempt += 1) {
    const parts = Object.fromEntries(
      formatter.formatToParts(new Date(instant)).map((part) => [part.type, part.value]),
    );
    const represented = Date.UTC(
      Number(parts.year),
      Number(parts.month) - 1,
      Number(parts.day),
      Number(parts.hour),
      Number(parts.minute),
    );
    instant += wanted - represented;
  }

  const finalParts = Object.fromEntries(
    formatter.formatToParts(new Date(instant)).map((part) => [part.type, part.value]),
  );
  const normalized = `${finalParts.year}-${finalParts.month}-${finalParts.day}T${finalParts.hour}:${finalParts.minute}`;
  if (normalized !== value) throw new Error("Horário local inválido para o fuso da unidade.");
  return new Date(instant).toISOString();
}

export async function createBookingAction(formData: FormData) {
  const unitId = required(formData, "unit_id");
  const resourceId = required(formData, "resource_id");
  const professionalId = required(formData, "professional_id");
  const timeZone = required(formData, "timezone");
  const startsAt = localDateTimeInZoneToIso(required(formData, "starts_at"), timeZone);
  const endsAt = localDateTimeInZoneToIso(required(formData, "ends_at"), timeZone);

  const availability = await getAvailability({ unitId, resourceId, startsAt, endsAt });
  const resourceAvailability = availability.resources.find((item) => item.resource_id === resourceId);
  if (!resourceAvailability?.available) {
    throw new Error(resourceAvailability?.reason ?? "O espaço não está disponível nesse período.");
  }

  await createBooking({
    unitId,
    resourceId,
    professionalId,
    startsAt,
    endsAt,
    notes: optional(formData, "notes"),
  });
  revalidatePath("/agenda");
  revalidatePath("/");
  redirect("/agenda");
}

export async function confirmBookingAction(formData: FormData) {
  await confirmBooking(required(formData, "booking_id"));
  revalidatePath("/agenda");
  revalidatePath("/");
}

export async function checkInAction(formData: FormData) {
  const usage = await checkInBooking(required(formData, "booking_id"));
  revalidatePath("/");
  redirect(`/operacao?usage=${encodeURIComponent(usage.id)}`);
}

export async function checkOutAction(formData: FormData) {
  await checkOutUsage(required(formData, "usage_id"));
  revalidatePath("/");
  redirect("/financeiro");
}

export async function closeInvoiceAction(formData: FormData) {
  await closeManualInvoice(required(formData, "invoice_id"));
  revalidatePath("/financeiro");
}

export async function confirmPixAction(formData: FormData) {
  const invoiceId = required(formData, "invoice_id");
  const amount = required(formData, "amount");
  const reference = formData.get("reference");

  await confirmPixPayment({
    invoiceId,
    amount,
    idempotencyKey: `web-${invoiceId}-${Date.now()}`,
    reference:
      typeof reference === "string" && reference.trim() !== ""
        ? reference.trim()
        : undefined,
  });
  revalidatePath("/financeiro");
}
