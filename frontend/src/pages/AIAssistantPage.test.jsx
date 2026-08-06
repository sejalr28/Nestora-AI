import { describe, it, expect, vi, beforeEach, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AIAssistantPage from "./AIAssistantPage";
import { assistantApi } from "../api/assistant";

vi.mock("../api/assistant", () => ({ assistantApi: { chat: vi.fn() } }));

beforeAll(() => {
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
});

beforeEach(() => {
    vi.clearAllMocks();
});

describe("AIAssistantPage", () => {
    it("shows an empty-state prompt before any messages", () => {
        render(<AIAssistantPage />);
        expect(screen.getByText(/Ask about water timings/)).toBeInTheDocument();
    });

    it("sends a message on Enter and renders both bubbles", async () => {
        const user = userEvent.setup();
        assistantApi.chat.mockResolvedValue({ reply: "Corporation water: 8-10 AM." });

        render(<AIAssistantPage />);
        const textarea = screen.getByLabelText("Message the AI Assistant");
        await user.type(textarea, "when's water today?{Enter}");

        expect(await screen.findByText("Corporation water: 8-10 AM.")).toBeInTheDocument();
        expect(screen.getByText("when's water today?")).toBeInTheDocument();
        expect(assistantApi.chat).toHaveBeenCalledWith("when's water today?", []);
    });

    it("inserts a newline on Shift+Enter instead of sending", async () => {
        const user = userEvent.setup();
        render(<AIAssistantPage />);
        const textarea = screen.getByLabelText("Message the AI Assistant");

        await user.type(textarea, "line one");
        await user.keyboard("{Shift>}{Enter}{/Shift}");
        await user.type(textarea, "line two");

        expect(textarea).toHaveValue("line one\nline two");
        expect(assistantApi.chat).not.toHaveBeenCalled();
    });

    it("shows a loading indicator while waiting for a reply", async () => {
        const user = userEvent.setup();
        let resolveChat;
        assistantApi.chat.mockReturnValue(
            new Promise((resolve) => {
                resolveChat = resolve;
            })
        );

        render(<AIAssistantPage />);
        await user.type(screen.getByLabelText("Message the AI Assistant"), "hi{Enter}");

        expect(screen.getByText("Thinking…")).toBeInTheDocument();
        resolveChat({ reply: "Hello!" });
        expect(await screen.findByText("Hello!")).toBeInTheDocument();
    });

    it("sends conversation history on the second message", async () => {
        const user = userEvent.setup();
        assistantApi.chat
            .mockResolvedValueOnce({ reply: "8-10 AM" })
            .mockResolvedValueOnce({ reply: "9 PM - 1 AM" });

        render(<AIAssistantPage />);
        const textarea = screen.getByLabelText("Message the AI Assistant");

        await user.type(textarea, "corp water?{Enter}");
        await screen.findByText("8-10 AM");

        await user.type(textarea, "bore water?{Enter}");
        await screen.findByText("9 PM - 1 AM");

        expect(assistantApi.chat).toHaveBeenLastCalledWith("bore water?", [
            { role: "user", content: "corp water?" },
            { role: "assistant", content: "8-10 AM" },
        ]);
    });

    it("shows an error with retry and restores the message on success", async () => {
        const user = userEvent.setup();
        assistantApi.chat.mockRejectedValueOnce(new Error("Network down"));

        render(<AIAssistantPage />);
        await user.type(screen.getByLabelText("Message the AI Assistant"), "hi{Enter}");

        expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't reach the assistant: Network down");

        assistantApi.chat.mockResolvedValueOnce({ reply: "Hello!" });
        await user.click(screen.getByRole("button", { name: "Retry" }));

        expect(await screen.findByText("Hello!")).toBeInTheDocument();
        expect(screen.getByText("hi")).toBeInTheDocument();
    });

    it("does not send an empty or whitespace-only message", async () => {
        const user = userEvent.setup();
        render(<AIAssistantPage />);
        await user.type(screen.getByLabelText("Message the AI Assistant"), "   {Enter}");
        expect(assistantApi.chat).not.toHaveBeenCalled();
    });

    it("clears the conversation when Clear conversation is clicked", async () => {
        const user = userEvent.setup();
        assistantApi.chat.mockResolvedValue({ reply: "Hello!" });

        render(<AIAssistantPage />);
        await user.type(screen.getByLabelText("Message the AI Assistant"), "hi{Enter}");
        await screen.findByText("Hello!");

        await user.click(screen.getByRole("button", { name: "Clear conversation" }));

        expect(screen.queryByText("hi")).not.toBeInTheDocument();
        expect(screen.queryByText("Hello!")).not.toBeInTheDocument();
        expect(screen.getByText(/Ask about water timings/)).toBeInTheDocument();
    });
});