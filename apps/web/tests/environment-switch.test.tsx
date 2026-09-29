import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => mocks }));

import { EnvironmentSwitch } from "../components/environment-switch";

describe("customer environment switch", () => {
  it("clears the selected tenant before returning to access selection", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);

    render(<EnvironmentSwitch />);
    fireEvent.click(screen.getByRole("button", { name: "Trocar ambiente" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/session/tenant", { method: "POST" }));
    expect(mocks.push).toHaveBeenCalledWith("/acesso");
    expect(mocks.refresh).toHaveBeenCalled();
  });
});
