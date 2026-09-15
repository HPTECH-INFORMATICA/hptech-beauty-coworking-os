import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AgendaPage from "../app/agenda/page";
import HomePage from "../app/page";
import {
  getBookings,
  getProfessionals,
  getResources,
  getUnits,
} from "../lib/bcos-api";

vi.mock("../lib/bcos-api", () => ({
  getBookings: vi.fn(),
  getProfessionals: vi.fn(),
  getResources: vi.fn(),
  getUnits: vi.fn(),
}));

const mockedGetUnits = vi.mocked(getUnits);
const mockedGetResources = vi.mocked(getResources);
const mockedGetProfessionals = vi.mocked(getProfessionals);
const mockedGetBookings = vi.mocked(getBookings);

beforeEach(() => {
  mockedGetUnits.mockResolvedValue([
    {
      id: "unit-1",
      name: "La Beauté Batel",
      timezone: "America/Sao_Paulo",
      active: true,
      created_at: "2026-09-15T00:00:00Z",
      updated_at: "2026-09-15T00:00:00Z",
    },
  ]);
  mockedGetResources.mockResolvedValue([]);
  mockedGetProfessionals.mockResolvedValue([]);
  mockedGetBookings.mockResolvedValue([]);
});

describe("operational navigation", () => {
  it("links the reception shell to real operational routes", async () => {
    render(await HomePage());

    expect(screen.getByRole("link", { name: "Agenda" })).toHaveAttribute(
      "href",
      "/agenda",
    );
    expect(screen.getByRole("link", { name: "Check-in" })).toHaveAttribute(
      "href",
      "/check-in",
    );
    expect(screen.getByRole("link", { name: "Financeiro" })).toHaveAttribute(
      "href",
      "/financeiro",
    );
    expect(screen.queryByText("CentralCheck-inFinanceiro")).not.toBeInTheDocument();
  });

  it("materializes agenda as a real route", async () => {
    render(await AgendaPage());

    expect(
      screen.getByRole("heading", { level: 1, name: "Agenda operacional" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voltar para a central" })).toHaveAttribute(
      "href",
      "/",
    );
  });
});
