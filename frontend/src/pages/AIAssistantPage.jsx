import { useEffect, useRef, useState } from "react";
import { assistantApi } from "../api/assistant";
import { ErrorState } from "../components/ErrorState";

export default function AIAssistantPage() {
    const [messages, setMessages] = useState([]); // { role: "user" | "assistant", content }
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [lastFailedMessage, setLastFailedMessage] = useState(null);
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    async function send(messageText) {
        const text = (messageText ?? input).trim();
        if (!text || loading) return;

        setError(null);
        setLastFailedMessage(null);
        const history = messages.map(({ role, content }) => ({ role, content }));
        const previousMessages = messages;
        setMessages([...previousMessages, { role: "user", content: text }]);
        setInput("");
        setLoading(true);

        try {
            const { reply } = await assistantApi.chat(text, history);
            setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
        } catch (err) {
            setError(err.message);
            setLastFailedMessage(text);
            // Roll back the optimistic user bubble so retry doesn't duplicate it.
            setMessages(previousMessages);
        } finally {
            setLoading(false);
        }
    }

    function handleKeyDown(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            send();
        }
    }

    function retry() {
        if (lastFailedMessage) send(lastFailedMessage);
    }

    function clearConversation() {
        setMessages([]);
        setError(null);
        setLastFailedMessage(null);
    }

    return (
        <div className="flex flex-col h-[calc(100vh-140px)]">
            <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold text-slate-800">AI Assistant</h2>
                {messages.length > 0 && (
                    <button
                        onClick={clearConversation}
                        className="text-sm font-medium text-slate-800 border border-slate-800 rounded px-3 py-1.5 hover:bg-slate-800/5"
                    >
                        Clear conversation
                    </button>
                )}
            </div>

            <div
                role="log"
                aria-live="polite"
                className="flex-1 overflow-y-auto bg-white border border-stone-300 rounded p-4 flex flex-col gap-3"
            >
                {messages.length === 0 && !loading && (
                    <p className="text-sm text-stone-500 text-center py-8">
                        Ask about water timings, flat status, or anything else the Society Assistant can help with.
                    </p>
                )}

                {messages.map((m, i) => (
                    <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div
                            className={
                                "max-w-[80%] rounded px-3 py-2 text-sm whitespace-pre-wrap " +
                                (m.role === "user"
                                    ? "bg-slate-800 text-white"
                                    : "bg-stone-100 text-stone-900 border border-stone-300")
                            }
                        >
                            {m.content}
                        </div>
                    </div>
                ))}

                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-stone-100 border border-stone-300 rounded px-3 py-2 text-sm text-stone-500">
                            Thinking…
                        </div>
                    </div>
                )}

                <div ref={bottomRef} />
            </div>

            {error && (
                <div className="mt-3">
                    <ErrorState message={`Couldn't reach the assistant: ${error}`} onRetry={retry} />
                </div>
            )}

            <div className="mt-3 flex gap-2 items-end">
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={loading}
                    rows={2}
                    placeholder="Ask the Society Assistant… (Enter to send, Shift+Enter for a new line)"
                    aria-label="Message the AI Assistant"
                    className="flex-1 border border-stone-400 rounded px-3 py-2 text-sm text-stone-900 resize-none disabled:opacity-50"
                />
                <button
                    onClick={() => send()}
                    disabled={loading || !input.trim()}
                    className="bg-slate-800 text-white text-sm font-medium rounded px-4 py-2 disabled:opacity-50 h-fit"
                >
                    Send
                </button>
            </div>
        </div>
    );
}