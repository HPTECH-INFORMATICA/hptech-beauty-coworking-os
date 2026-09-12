import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "../app/page";

describe("HomePage", () => {
  it("renders the reception operational dashboard", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Visão geral",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Central da Recepção"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "Controle da operação em um só lugar.",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("navigation", {
        name: "Navegação principal",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("region", {
        name: "Indicadores operacionais",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        level: 3,
        name: "Agenda e uso real",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        level: 3,
        name: "Faturamento",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        level: 3,
        name: "Recursos do coworking",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Fluxo financeiro validado"),
    ).toBeInTheDocument();
  });
});