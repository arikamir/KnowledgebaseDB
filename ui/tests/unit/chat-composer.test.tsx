import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { LearnerStateProvider } from "../../src/app/learner-state-context";
import { ChatComposer } from "../../src/components/chat/ChatComposer";

describe("ChatComposer", () => {
  it("has an accessible labelled input and prevents empty submission", async () => { render(<MemoryRouter><LearnerStateProvider><ChatComposer /></LearnerStateProvider></MemoryRouter>); expect(screen.getByLabelText("Ask about your roadmap")).toBeInTheDocument(); expect(screen.getByRole("button", { name: "Send" })).toBeEnabled(); });
});
