import { useState } from "react";
import { workflowsApi } from "../api/workflows";
import { ErrorState } from "../components/ErrorState";

const STEP_STATUS_STYLE = {
  done: "border-emerald-600 text-emerald-700",
  error: "border-red-600 text-red-700",
};

const EXAMPLE_GOALS = [
  "Assign an available plumber to every open plumbing request",
  "Summarize our current occupancy and service request status",
  "Find an available electrician for any open electrical requests",
];

export default function WorkflowsPage() {
  const [goal, setGoal] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [outcome, setOutcome] = useState(null);

  async function run(goalText) {
    const text = (goalText ?? goal).trim();
    if (!text || running) return;

    setRunning(true);
    setError(null);
    setOutcome(null);
    try {
      const result = await workflowsApi.run(text);
      setOutcome(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  }

  function retry() {
    if (goal.trim()) run(goal);
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-slate-800">Workflows</h2>
      <p className="text-sm text-stone-500">
        Describe a goal and the assistant will plan and carry out the steps automatically —
        e.g. finding an available vendor and assigning them to open requests.
      </p>

      <div className="bg-white border border-stone-300 rounded p-4 flex flex-col gap-3">
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          disabled={running}
          rows={2}
          placeholder="e.g. Assign an available plumber to every open plumbing request"
          aria-label="Workflow goal"
          className="border border-stone-400 rounded px-3 py-2 text-sm text-stone-900 resize-none disabled:opacity-50"
        />

        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLE_GOALS.map((example) => (
              <button
                key={example}
                onClick={() => setGoal(example)}
                disabled={running}
                className="text-xs text-stone-500 border border-stone-300 rounded px-2 py-1 hover:border-stone-500 disabled:opacity-50"
              >
                {example}
              </button>
            ))}
          </div>

          <button
            onClick={() => run()}
            disabled={running || !goal.trim()}
            className="bg-slate-800 text-white text-sm font-medium rounded px-4 py-2 disabled:opacity-50 shrink-0"
          >
            {running ? "Running…" : "Run workflow"}
          </button>
        </div>
      </div>

      {error && <ErrorState message={`Couldn't run the workflow: ${error}`} onRetry={retry} />}

      {outcome && (
        <div className="flex flex-col gap-3">
          <div className="bg-white border border-stone-300 border-l-4 border-l-slate-800 rounded p-4">
            <div className="text-[11px] uppercase tracking-wide text-stone-500 font-semibold mb-1">
              Summary
            </div>
            <div className="text-sm text-stone-800 whitespace-pre-wrap">{outcome.summary}</div>
          </div>

          {outcome.results.length > 0 && (
            <div className="flex flex-col gap-2">
              <div className="text-xs font-semibold text-stone-600 uppercase tracking-wide">
                Steps ({outcome.results.length})
              </div>
              {outcome.results.map((r) => (
                <div key={r.step} className="bg-white border border-stone-300 rounded px-4 py-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`text-[10px] font-semibold uppercase tracking-wide border rounded px-1.5 py-0.5 ${STEP_STATUS_STYLE[r.status] || ""}`}
                    >
                      {r.status}
                    </span>
                    <span className="text-sm font-medium text-stone-900">
                      Step {r.step}: {r.tool}
                    </span>
                  </div>
                  {r.reason && <div className="text-sm text-stone-600 mt-1">{r.reason}</div>}
                  <pre className="text-xs text-stone-500 bg-stone-50 border border-stone-200 rounded p-2 mt-2 overflow-x-auto">
                    {JSON.stringify(r.result, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}