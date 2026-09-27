"use server";

import { redirect } from "next/navigation";

import { createMyBooking } from "../../lib/bcos-api";

function value(formData: FormData, name: string): string {
  return String(formData.get(name) ?? "").trim();
}

export async function createMyBookingAction(formData: FormData) {
  const startsAt = value(formData, "starts_at");
  const endsAt = value(formData, "ends_at");
  await createMyBooking({
    unitId: value(formData, "unit_id"),
    resourceId: value(formData, "resource_id"),
    startsAt,
    endsAt,
    notes: value(formData, "notes") || undefined,
  });
  redirect("/profissional?created=booking");
}
