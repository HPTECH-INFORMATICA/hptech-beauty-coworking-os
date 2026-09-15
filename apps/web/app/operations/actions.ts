"use server";

import { revalidatePath } from "next/cache";

import {
  checkInBooking,
  checkOutUsage,
  closeManualInvoice,
  confirmPixPayment,
} from "../../lib/bcos-api";

function required(formData: FormData, name: string): string {
  const value = formData.get(name);
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Campo obrigatório ausente: ${name}`);
  }
  return value.trim();
}

export async function checkInAction(formData: FormData) {
  await checkInBooking(required(formData, "booking_id"));
  revalidatePath("/");
}

export async function checkOutAction(formData: FormData) {
  await checkOutUsage(required(formData, "usage_id"));
  revalidatePath("/");
}

export async function closeInvoiceAction(formData: FormData) {
  await closeManualInvoice(required(formData, "invoice_id"));
  revalidatePath("/");
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
  revalidatePath("/");
}
