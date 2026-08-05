import { useEffect, useState } from "react";
import { serviceRequestsApi } from "../api/serviceRequests";
import { buildingsApi } from "../api/buildings";
import { flatsApi } from "../api/flats";
import { vendorsApi } from "../api/vendors";

const CATEGORIES = ["Plumber", "Electrician", "Carpenter", "Pest Control"];
const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "open", label: "Open" },
  { value: "assigned", label: "Assigned" },
  { value: "done", label: "Done" },
];
const STATUS_STYLE = {
  open: "border-amber-600 text-amber-700",
  assigned: "border-blue-600 text-blue-700",
  done: "border-emerald-600 text-emerald-700",
};

export default function ServiceRequestsPage() {
  const [requests, setRequests] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [statusFilter, setStatusFilter] = useState("");

  const [buildings, setBuildings] = useState(null);
  const [showLogForm, setShowLogForm] = useState(false);
  const [logBuildingId, setLogBuildingId] = useState("");
  const [logAvailableFlats, setLogAvailableFlats] = useState(null);
  const [logDraft, setLogDraft] = useState({ flat_id: "", category: CATEGORIES[0], description: "" });
  const [logError, setLogError] = useState(null);
  const [logSaving, setLogSaving] = useState(false);

  const [assigningRequestId, setAssigningRequestId] = useState(null);
  const [assignVendors, setAssignVendors] = useState(null);
  const [assignDraft, setAssignDraft] = useState({ vendor_id: "", assigned_slot: "" });
  const [assignError, setAssignError] = useState(null);
  const [assignSaving, setAssignSaving] = useState(false);

  const [completingId, setCompletingId] = useState(null);

  useEffect(() => {
    load();
  }, [statusFilter]);

  useEffect(() => {
    buildingsApi.list().then(setBuildings).catch((err) => setLogError(err.message));
  }, []);

  useEffect(() => {
    if (!logBuildingId) {
      setLogAvailableFlats(null);
      return;
    }
    flatsApi.listByBuilding(logBuildingId).then(setLogAvailableFlats).catch((err) => setLogError(err.message));
  }, [logBuildingId]);

  async function load() {
    setLoadError(null);
    try {
      const data = await serviceRequestsApi.list({ status: statusFilter });
      setRequests(data);
    } catch (err) {
      setLoadError(err.message);
    }
  }

  async function logRequest() {
    if (!logDraft.flat_id) return;
    setLogSaving(true);
    setLogError(null);
    try {
      await serviceRequestsApi.create({
        flat_id: Number(logDraft.flat_id),
        category: logDraft.category,
        description: logDraft.description.trim() || null,
      });
      setShowLogForm(false);
      setLogBuildingId("");
      setLogDraft({ flat_id: "", category: CATEGORIES[0], description: "" });
      await load();
    } catch (err) {
      setLogError(err.message);
    } finally {
      setLogSaving(false);
    }
  }

  function startAssign(request) {
    setAssignError(null);
    setAssigningRequestId(request.id);
    setAssignDraft({ vendor_id: "", assigned_slot: "" });
    setAssignVendors(null);
    vendorsApi
      .list({ category: request.category, activeOnly: true })
      .then(setAssignVendors)
      .catch((err) => setAssignError(err.message));
  }

  async function saveAssign() {
    if (!assignDraft.vendor_id || !assignDraft.assigned_slot.trim()) return;
    setAssignSaving(true);
    setAssignError(null);
    try {
      await serviceRequestsApi.update(assigningRequestId, {
        status: "assigned",
        vendor_id: Number(assignDraft.vendor_id),
        assigned_slot: assignDraft.assigned_slot.trim(),
      });
      setAssigningRequestId(null);
      await load();
    } catch (err) {
      setAssignError(err.message);
    } finally {
      setAssignSaving(false);
    }
  }

  async function markDone(requestId) {
    setCompletingId(requestId);
    try {
      await serviceRequestsApi.update(requestId, { status: "done" });
      await load();
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setCompletingId(null);
    }
  }

  if (requests === null && !loadError) {
    return <p className="text-sm text-stone-500">Loading…</p>;
  }

  if (loadError) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded px-4 py-3 flex items-center justify-between gap-3">
        <span>Couldn't load service requests: {loadError}</span>
        <button onClick={load} className="font-medium underline shrink-0">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-lg font-semibold text-slate-800">Service Requests</h2>
        <button
          onClick={() => setShowLogForm((v) => !v)}
          className="text-sm font-medium text-slate-800 border border-slate-800 rounded px-3 py-1.5 hover:bg-slate-800/5"
        >
          + Log a request
        </button>
      </div>

      {showLogForm && (
        <div className="bg-white border border-stone-300 rounded p-4 flex flex-col gap-3">
          {logError && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
              {logError}
            </div>
          )}
          <div className="flex gap-3 flex-wrap items-end">
            <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
              Building
              <select
                value={logBuildingId}
                onChange={(e) => {
                  setLogBuildingId(e.target.value);
                  setLogDraft({ ...logDraft, flat_id: "" });
                }}
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
              >
                <option value="">Select…</option>
                {(buildings || []).map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
              Flat
              <select
                value={logDraft.flat_id}
                onChange={(e) => setLogDraft({ ...logDraft, flat_id: e.target.value })}
                disabled={!logBuildingId}
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900 disabled:opacity-50"
              >
                <option value="">Select…</option>
                {(logAvailableFlats || []).map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.flat_number}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
              Category
              <select
                value={logDraft.category}
                onChange={(e) => setLogDraft({ ...logDraft, category: e.target.value })}
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
              >
                {CATEGORIES.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
          </div>

          <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
            What's needed?
            <input
              type="text"
              value={logDraft.description}
              onChange={(e) => setLogDraft({ ...logDraft, description: e.target.value })}
              placeholder="e.g. kitchen tap leaking"
              className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
            />
          </label>

          {logBuildingId && logAvailableFlats !== null && logAvailableFlats.length === 0 && (
            <p className="text-xs text-stone-500">
              No flats recorded for this building yet — add one first from the Buildings page.
            </p>
          )}

          <div>
            <button
              onClick={logRequest}
              disabled={logSaving || !logDraft.flat_id}
              className="bg-slate-800 text-white text-sm font-medium rounded px-3 py-1.5 disabled:opacity-50"
            >
              {logSaving ? "Posting…" : "Post request"}
            </button>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={
              "text-sm font-medium rounded px-3 py-1.5 border " +
              (statusFilter === f.value
                ? "bg-slate-800 text-white border-slate-800"
                : "text-stone-700 border-stone-300 hover:border-stone-500")
            }
          >
            {f.label}
          </button>
        ))}
      </div>

      {requests.length === 0 ? (
        <p className="text-sm text-stone-500">No requests logged yet.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {requests.map((request) => (
            <div key={request.id} className="bg-white border border-stone-300 rounded p-4 flex flex-col gap-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className={`text-[10px] font-semibold uppercase tracking-wide border rounded px-1.5 py-0.5 ${STATUS_STYLE[request.status]}`}
                >
                  {request.status}
                </span>
                <span className="text-sm text-stone-600">
                  {request.category} · {request.flat.building.name}, Flat {request.flat.flat_number}
                  {request.requested_by?.name ? ` · ${request.requested_by.name}` : ""}
                </span>
              </div>

              {request.description && <div className="text-sm text-stone-800 italic">"{request.description}"</div>}

              {request.status === "open" &&
                (assigningRequestId === request.id ? (
                  <div className="border-t border-dashed border-stone-300 pt-2 mt-1 flex flex-col gap-2">
                    {assignError && (
                      <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
                        {assignError}
                      </div>
                    )}
                    {assignVendors === null ? (
                      <p className="text-xs text-stone-500">Loading vendors…</p>
                    ) : assignVendors.length === 0 ? (
                      <p className="text-xs text-stone-500">
                        No active {request.category} vendors — add one from the Vendors page.
                      </p>
                    ) : (
                      <div className="flex gap-2 flex-wrap items-end">
                        <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
                          Vendor
                          <select
                            value={assignDraft.vendor_id}
                            onChange={(e) => setAssignDraft({ ...assignDraft, vendor_id: e.target.value })}
                            className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
                          >
                            <option value="">Select…</option>
                            {assignVendors.map((v) => (
                              <option key={v.id} value={v.id}>
                                {v.name}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
                          Slot
                          <input
                            type="text"
                            value={assignDraft.assigned_slot}
                            onChange={(e) => setAssignDraft({ ...assignDraft, assigned_slot: e.target.value })}
                            placeholder="e.g. Tomorrow 9-10 AM"
                            className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
                          />
                        </label>
                        <button
                          onClick={saveAssign}
                          disabled={assignSaving || !assignDraft.vendor_id || !assignDraft.assigned_slot.trim()}
                          className="bg-slate-800 text-white text-sm font-medium rounded px-3 py-1.5 disabled:opacity-50"
                        >
                          {assignSaving ? "Booking…" : "Book"}
                        </button>
                        <button
                          onClick={() => setAssigningRequestId(null)}
                          disabled={assignSaving}
                          className="text-sm font-medium text-slate-800 border border-slate-800 rounded px-3 py-1.5 disabled:opacity-50"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <button
                    onClick={() => startAssign(request)}
                    className="self-start text-sm font-medium text-slate-800 border border-slate-800 rounded px-3 py-1.5"
                  >
                    Assign vendor
                  </button>
                ))}

              {request.status === "assigned" && (
                <div className="flex items-center gap-2 text-sm text-stone-700 flex-wrap">
                  Booked: <strong>{request.vendor?.name}</strong> · {request.assigned_slot}
                  <button
                    onClick={() => markDone(request.id)}
                    disabled={completingId === request.id}
                    className="ml-auto text-sm font-medium text-slate-800 border border-slate-800 rounded px-3 py-1.5 disabled:opacity-50"
                  >
                    {completingId === request.id ? "Saving…" : "Mark done"}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}