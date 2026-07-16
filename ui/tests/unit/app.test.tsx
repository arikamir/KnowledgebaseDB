import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { App } from "../../src/app/App";

describe("App", () => {
  it("renders the accessible application heading", () => {
    render(<MemoryRouter><App /></MemoryRouter>);
    expect(screen.getByRole("heading", { level: 1, name: "DevOps Career Agent" })).toBeVisible();
  });
});
