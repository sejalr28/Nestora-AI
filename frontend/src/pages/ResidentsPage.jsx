import { useEffect, useState } from "react";
import { residentsApi } from "../api/residents";
import { buildingsApi } from "../api/buildings";
import { flatsApi } from "../api/flats";

const ROLES = [
  { value: "", label: "Not set" },
  { value: "owner", label: "Owner" },
  { value: "tenant", label: "Tenant" },
];

export default function ResidentsPage() {
  const [residents, setResidents] = useState(null);
  const [buildings, setBuildings] = useState(null);
  const [flatsById, setFlatsById] = useState(null); // flat_id -> { buildingName, flatNumber }
  const [loadError, setLoadError] = useState(null);

  const [showAddForm, setShowAddForm] = useState(false);
  const [addBuildingId, setAddBuildingId] = useState("");
  const [addAvailableFlats, setAddAvailableFlats] = useState(null);
  const [addDraft, setAddDraft] = useState({ flat_id: "", name: "", phone_number: "", role: "" });
  const [addError, setAddError] = useState(null);
  const [addSaving, setAddSaving] = useState(false);

  const [editingResidentId, setEditingResidentId] = useState(null);
  const [editDraft, setEditDraft] = useState({ name: "", role: "" });
  const [editError, setEditError] = useState(null);
  const [editSaving, setEditSaving] = useState(false);

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    if (!addBuildingId) {
      setAddAvailableFlats(null);
      return;
    }
    flatsApi
      .listByBuilding(addBuildingId)
      .then(setAddAvailableFlats)
      .catch((err) => setAddError(err.message));
  }, [addBuildingId]);

  async function loadAll() {
    setLoadError(null);
    setResidents(null);
    try {
      const [buildingsData, residentsData] = await Promise.all([buildingsApi.list(), residentsApi.list()]);
      setBuildings(buildingsData);

      // ResidentRead doesn't include nested flat/building info, so we build
      // a flat_id -> "Building, Flat#" lookup ourselves from the APIs
      // Buildings/Flats pages already gave us -- no backend change needed.
      const perBuildingFlats = await Promise.all(
        buildingsData.map((b) =>
          flatsApi.listByBuilding(b.id).then((flats) => flats.map((f) => ({ ...f, buildingName: b.name })))
        )
      );
      const map = {};
      perBuildingFlats.flat().forEach((f) => {
        map[f.id] = { buildingName: f.buildingName, flatNumber: f.flat_number };
      });
      setFlatsById(map);

      setResidents(residentsData);
    } catch (err) {
      setLoadError(err.message);
    }
  }

  async function addResident() {
    if (!addDraft.flat_id || !addDraft.phone_number.trim()) return;
    setAddSaving(true);
    setAddError(null);
    try {
      await residentsApi.create({
        flat_id: Number(addDraft.flat_id),
        phone_number: addDraft.phone_number.trim(),
        name: addDraft.name.trim() || null,
        role: addDraft.role || null,
      });
      setShowAddForm(false);
      setAddBuildingId("");
      setAddDraft({ flat_id: "", name: "", phone_number: "", role: "" });
      await loadAll();
    } catch (err) {
      setAddError(err.message);
    } finally {
      setAddSaving(false);
    }
  }

  function startEdit(resident) {
    setEditError(null);
    setEditingResidentId(resident.id);
    setEditDraft({ name: resident.name || "", role: resident.role || "" });
  }

  async function saveEdit() {
    setEditSaving(true);
    setEditError(null);
    try {
      await residentsApi.update(editingResidentId, {
        name: editDraft.name.trim() || null,
        role: editDraft.role || null,
      });
      setEditingResidentId(null);
      await loadAll();
    } catch (err) {
      setEditError(err.message);
    } finally {
      setEditSaving(false);
    }
  }

  if (residents === null && !loadError) {
    return <p className="text-sm text-stone-500">Loading…</p>;
  }

  if (loadError) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded px-4 py-3 flex items-center justify-between gap-3">
        <span>Couldn't load residents: {loadError}</span>
        <button onClick={loadAll} className="font-medium underline shrink-0">
          Retry
        </button>
      </div>
    );
  }

  const editingResident = residents.find((r) => r.id === editingResidentId);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-lg font-semibold text-slate-800">Residents</h2>
        <button
          onClick={() => setShowAddForm((v) => !v)}
          className="text-sm font-medium text-slate-800 border border-slate-800 rounded px-3 py-1.5 hover:bg-slate-800/5"
        >
          + Add resident
        </button>
      </div>

      {showAddForm && (
        <div className="bg-white border border-stone-300 rounded p-4 flex flex-col gap-3">
          {addError && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
              {addError}
            </div>
          )}
          <div className="flex gap-3 flex-wrap items-end">
            <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
              Building
              <select
                value={addBuildingId}
                onChange={(e) => {
                  setAddBuildingId(e.target.value);
                  setAddDraft({ ...addDraft, flat_id: "" });
                }}
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
              >
                <option value="">Select…</option>
                {buildings.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
              Flat
              <select
                value={addDraft.flat_id}
                onChange={(e) => setAddDraft({ ...addDraft, flat_id: e.target.value })}
                disabled={!addBuildingId}
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900 disabled:opacity-50"
              >
                <option value="">Select…</option>
                {(addAvailableFlats || []).map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.flat_number}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex-1 min-w-[140px] text-xs text-stone-500 font-medium flex flex-col gap-1">
              Name
              <input
                type="text"
                value={addDraft.name}
                onChange={(e) => setAddDraft({ ...addDraft, name: e.target.value })}
                placeholder="e.g. Priya Deshmukh"
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
              />
            </label>

            <label className="flex-1 min-w-[140px] text-xs text-stone-500 font-medium flex flex-col gap-1">
              Phone number
              <input
                type="text"
                value={addDraft.phone_number}
                onChange={(e) => setAddDraft({ ...addDraft, phone_number: e.target.value })}
                placeholder="e.g. +919876543210"
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
              />
            </label>

            <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
              Role
              <select
                value={addDraft.role}
                onChange={(e) => setAddDraft({ ...addDraft, role: e.target.value })}
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
              >
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </label>

            <button
              onClick={addResident}
              disabled={addSaving || !addDraft.flat_id || !addDraft.phone_number.trim()}
              className="bg-slate-800 text-white text-sm font-medium rounded px-3 py-1.5 disabled:opacity-50"
            >
              {addSaving ? "Adding…" : "Add"}
            </button>
          </div>

          {addBuildingId && addAvailableFlats !== null && addAvailableFlats.length === 0 && (
            <p className="text-xs text-stone-500">
              No flats recorded for this building yet — add one first from the Buildings page.
            </p>
          )}
        </div>
      )}

      {residents.length === 0 ? (
        <p className="text-sm text-stone-500">No residents yet.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {residents.map((resident) => {
            const flatInfo = flatsById[resident.flat_id];
            return (
              <div
                key={resident.id}
                className="bg-white border border-stone-300 border-l-4 border-l-slate-800 rounded px-4 py-3 flex items-center justify-between gap-3 flex-wrap"
              >
                <div>
                  <div className="font-medium text-stone-900">
                    {resident.name || <span className="text-stone-400 italic">No name on file</span>}
                    {resident.role && (
                      <span className="ml-2 text-[10px] font-semibold uppercase tracking-wide text-stone-500 border border-stone-400 rounded px-1.5 py-0.5">
                        {resident.role}
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-stone-500">
                    {flatInfo ? `${flatInfo.buildingName}, Flat ${flatInfo.flatNumber}` : `Flat #${resident.flat_id}`}
                    {" · "}
                    <a href={`tel:${resident.phone_number}`} className="hover:underline">
                      {resident.phone_number}
                    </a>
                  </div>
                </div>
                <button
                  onClick={() => startEdit(resident)}
                  className="text-sm font-medium text-slate-800 border border-slate-800 rounded px-3 py-1.5 shrink-0"
                >
                  Edit
                </button>
              </div>
            );
          })}
        </div>
      )}

      {editingResident && (
        <div className="fixed inset-0 bg-stone-900/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded p-5 w-full max-w-sm border-t-4 border-amber-600 flex flex-col gap-3">
            <h3 className="font-semibold text-slate-800">{editingResident.phone_number}</h3>

            {editError && (
              <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
                {editError}
              </div>
            )}

            <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
              Name
              <input
                type="text"
                value={editDraft.name}
                onChange={(e) => setEditDraft({ ...editDraft, name: e.target.value })}
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
              />
            </label>

            <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
              Role
              <select
                value={editDraft.role}
                onChange={(e) => setEditDraft({ ...editDraft, role: e.target.value })}
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
              >
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="flex gap-2 mt-1">
              <button
                onClick={saveEdit}
                disabled={editSaving}
                className="bg-slate-800 text-white text-sm font-medium rounded px-3 py-1.5 disabled:opacity-50"
              >
                {editSaving ? "Saving…" : "Save"}
              </button>
              <button
                onClick={() => setEditingResidentId(null)}
                disabled={editSaving}
                className="text-sm font-medium text-slate-800 border border-slate-800 rounded px-3 py-1.5 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}