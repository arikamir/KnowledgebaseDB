import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LearnerStateProvider, useLearnerState } from "../../src/app/learner-state-context";
import { ChatConversation } from "../../src/components/chat/ChatConversation";

function Seeded() { const { dispatch } = useLearnerState(); return <><button type="button" onClick={() => dispatch({ type: "pending", message: { id: "u", role: "user", text: "Question", createdAt: "now" } })}>seed</button><ChatConversation /></>; }
describe("ChatConversation", () => { it("renders a semantic log and speaker labels", () => { render(<LearnerStateProvider><Seeded /></LearnerStateProvider>); expect(screen.getByRole("log")).toBeInTheDocument(); expect(screen.getByRole("button", { name: "Reset conversation" })).toBeInTheDocument(); }); });
