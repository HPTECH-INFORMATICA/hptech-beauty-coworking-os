import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "../app/page";

describe("HomePage", () => {
  it("renders the technical application skeleton", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "HPTECH Beauty Coworking OS",
      }),
    ).toBeInTheDocument();

    expect(screen.getByText("Application skeleton operational.")).toBeInTheDocument();
  });
});
