import { useEffect, useState } from "react";
import { waterScheduleApi } from "../api/waterSchedule";

const SOURCE_LABELS = {
  corporation: "Corporation Water",
  bore: "Bore Water (Hard Water)",
};

const SOURCES = ["corporation", "bore"];

function formatTime(t) {
  // API returns "HH:MM:SS" -- render as "8:00 AM"
  const [h, m] = t.split(":").map(Number);
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, "0")} ${ampm}`;
}

function toApiTime(t) {
  // <input type="time"> gives "HH:MM" -- API wants "HH:MM:SS"
  return t.length === 5 ? `${t}:00` : t;
}

function toInputTime(t) {
  // API gives "HH:MM:SS" -- <input type="time"> wants "HH:MM"
  return t.slice(0, 5);
}

export default function WaterSchedulePage() {
  const [schedules, setSchedules] = useState(null); // null while loading
  const [loadError, setLoadError] = useState(null);
  const [editingSource, setEditingSource] = useState(null);
  const [draft, setDraft] = useState(null);
  const [saveError, setSaveError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoadError(null);
    try {
      const data = await waterScheduleApi.list();
      setSchedules(data);
    } catch (err) {
      setLoadError(err.message);
    }
  }

  function startEdit(source, existing) {
    setSaveError(null);
    setEditingSource(source);
    setDraft(
      existing
        ? {
            start_time: toInputTime(existing.start_time),
            end_time: toInputTime(existing.end_time),
            note: existing.note || "",
          }
        : { start_time: "08:00", end_time: "10:00", note: "" }
    );
  }

  async function save() {
    setSaving(true);
    setSaveError(null);
    try {
      await waterScheduleApi.update(editingSource, {
        start_time: toApiTime(draft.start_time),
        end_time: toApiTime(draft.end_time),
        note: draft.note,
        updated_by: "Committee",
      });
      setEditingSource(null);
      await load();
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (schedules === null && !loadError) {
    return <p className="text-sm text-stone-500">Loading…</p>;
  }

  if (loadError) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded px-4 py-3 flex items-center justify-between gap-3">
        <span>Couldn't load the water schedule: {loadError}</span>
        <button onClick={load} className="font-medium underline shrink-0">
          Retry
        </button>
      </div>
    );
  }

  const bySource = Object.fromEntries(schedules.map((s) => [s.source, s]));

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-slate-800">Water Schedule</h2>

      <div className="grid sm:grid-cols-2 gap-4">
        {SOURCES.map((source) => {
          const existing = bySource[source];
          return (
            <div
              key={source}
              className="bg-white border border-stone-300 border-l-4 border-l-slate-800 rounded p-4"
            >
              <div className="text-[11px] uppercase tracking-wide text-stone-500 font-semibold">
                {SOURCE_LABELS[source]}
              </div>

              {existing ? (
                <>
                  <div className="font-mono text-xl text-slate-800 my-1">
                    {formatTime(existing.start_time)} – {formatTime(existing.end_time)}
                  </div>
                  {existing.note && <div className="text-sm text-stone-500">{existing.note}</div>}
                </>
              ) : (
                <div className="text-sm text-stone-500 my-2">Not set yet.</div>
              )}

              <button
                onClick={() => startEdit(source, existing)}
                className="mt-3 text-sm font-medium text-slate-800 border border-slate-800 rounded px-3 py-1.5 hover:bg-slate-800/5"
              >
                {existing ? "Update timing" : "Set timing"}
              </button>
            </div>
          );
        })}
      </div>

      {editingSource && (
        <div className="fixed inset-0 bg-stone-900/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded p-5 w-full max-w-sm border-t-4 border-amber-600 flex flex-col gap-3">
            <h3 className="font-semibold text-slate-800">{SOURCE_LABELS[editingSource]}</h3>

            {saveError && (
              <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
                {saveError}
              </div>
            )}

            <div className="flex gap-3">
              <label className="flex-1 text-xs text-stone-500 font-medium flex flex-col gap-1">
                Start
                <input
                  type="time"
                  value={draft.start_time}
                  onChange={(e) => setDraft({ ...draft, start_time: e.target.value })}
                  className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
                />
              </label>
              <label className="flex-1 text-xs text-stone-500 font-medium flex flex-col gap-1">
                End
                <input
                  type="time"
                  value={draft.end_time}
                  onChange={(e) => setDraft({ ...draft, end_time: e.target.value })}
                  className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
                />
              </label>
            </div>

            <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
              Note
              <input
                type="text"
                value={draft.note}
                onChange={(e) => setDraft({ ...draft, note: e.target.value })}
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
                placeholder="e.g. Municipal line — fill early"
              />
            </label>

            <div className="flex gap-2 mt-1">
              <button
                onClick={save}
                disabled={saving}
                className="bg-slate-800 text-white text-sm font-medium rounded px-3 py-1.5 disabled:opacity-50"
              >
                {saving ? "Saving…" : "Post update"}
              </button>
              <button
                onClick={() => setEditingSource(null)}
                disabled={saving}
                className="text-sm font-medium text-slate-800 border border-slate-800 rounded px-3 py-1.5 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <p className="text-xs text-stone-500">
        Only buildings with a bore pump installed receive bore water — check each building's record if unsure.
      </p>
    </div>
  );
}