import { useEffect, useState } from "react";
import { buildingsApi } from "../api/buildings";
import { flatsApi } from "../api/flats";

const FLOORS = [4, 3, 2, 1]; // top-down, matches the original prototype's directory
const UNITS = [1, 2, 3, 4];
const FLAT_NUMBERS = FLOORS.flatMap((floor) => UNITS.map((unit) => floor * 100 + unit));

const STATUS_STYLE = {
  vacant: { label: "VACANT", classes: "border-emerald-600 text-emerald-700" },
  owner: { label: "OWNER", classes: "border-blue-600 text-blue-700" },
  rented: { label: "RENTED", classes: "border-amber-600 text-amber-700" },
  unknown: { label: "UNSET", classes: "border-stone-400 text-stone-500" },
};

export default function BuildingsPage() {
  const [buildings, setBuildings] = useState(null);
  const [buildingsError, setBuildingsError] = useState(null);
  const [selectedBuildingId, setSelectedBuildingId] = useState(null);

  const [showAddBuilding, setShowAddBuilding] = useState(false);
  const [addDraft, setAddDraft] = useState({ name: "", has_bore_water: false });
  const [addError, setAddError] = useState(null);
  const [addSaving, setAddSaving] = useState(false);

  const [flatsByNumber, setFlatsByNumber] = useState(null);
  const [flatsError, setFlatsError] = useState(null);

  const [editingFlatNumber, setEditingFlatNumber] = useState(null);
  const [flatStatusDraft, setFlatStatusDraft] = useState("unknown");
  const [flatSaveError, setFlatSaveError] = useState(null);
  const [flatSaving, setFlatSaving] = useState(false);

  useEffect(() => {
    loadBuildings();
  }, []);

  useEffect(() => {
    if (selectedBuildingId != null) loadFlats(selectedBuildingId);
  }, [selectedBuildingId]);

  async function loadBuildings() {
    setBuildingsError(null);
    try {
      const data = await buildingsApi.list();
      setBuildings(data);
      if (data.length > 0 && selectedBuildingId == null) {
        setSelectedBuildingId(data[0].id);
      }
    } catch (err) {
      setBuildingsError(err.message);
    }
  }

  async function loadFlats(buildingId) {
    setFlatsError(null);
    setFlatsByNumber(null);
    try {
      const data = await flatsApi.listByBuilding(buildingId);
      setFlatsByNumber(Object.fromEntries(data.map((f) => [f.flat_number, f])));
    } catch (err) {
      setFlatsError(err.message);
    }
  }

  async function addBuilding() {
    if (!addDraft.name.trim()) return;
    setAddSaving(true);
    setAddError(null);
    try {
      const building = await buildingsApi.create(addDraft);
      setBuildings((prev) => [...prev, building].sort((a, b) => a.name.localeCompare(b.name)));
      setSelectedBuildingId(building.id);
      setShowAddBuilding(false);
      setAddDraft({ name: "", has_bore_water: false });
    } catch (err) {
      setAddError(err.message);
    } finally {
      setAddSaving(false);
    }
  }

  function openFlatEditor(flatNumber) {
    setFlatSaveError(null);
    setEditingFlatNumber(flatNumber);
    setFlatStatusDraft(flatsByNumber[flatNumber]?.status || "unknown");
  }

  async function saveFlatStatus() {
    setFlatSaving(true);
    setFlatSaveError(null);
    try {
      const existing = flatsByNumber[editingFlatNumber];
      if (existing) {
        await flatsApi.update(existing.id, { status: flatStatusDraft });
      } else {
        await flatsApi.create({
          building_id: selectedBuildingId,
          flat_number: editingFlatNumber,
          status: flatStatusDraft,
        });
      }
      setEditingFlatNumber(null);
      await loadFlats(selectedBuildingId);
    } catch (err) {
      setFlatSaveError(err.message);
    } finally {
      setFlatSaving(false);
    }
  }

  if (buildings === null && !buildingsError) {
    return <p className="text-sm text-stone-500">Loading…</p>;
  }

  if (buildingsError) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded px-4 py-3 flex items-center justify-between gap-3">
        <span>Couldn't load buildings: {buildingsError}</span>
        <button onClick={loadBuildings} className="font-medium underline shrink-0">
          Retry
        </button>
      </div>
    );
  }

  const selectedBuilding = buildings.find((b) => b.id === selectedBuildingId);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Buildings</h2>
        <button
          onClick={() => setShowAddBuilding((v) => !v)}
          className="text-sm font-medium text-slate-800 border border-slate-800 rounded px-3 py-1.5 hover:bg-slate-800/5"
        >
          + Add building
        </button>
      </div>

      {showAddBuilding && (
        <div className="bg-white border border-stone-300 rounded p-4 flex flex-col gap-3">
          {addError && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
              {addError}
            </div>
          )}
          <div className="flex gap-3 flex-wrap items-end">
            <label className="flex-1 min-w-[160px] text-xs text-stone-500 font-medium flex flex-col gap-1">
              Building name
              <input
                type="text"
                value={addDraft.name}
                onChange={(e) => setAddDraft({ ...addDraft, name: e.target.value })}
                placeholder="e.g. Building 16"
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
              />
            </label>
            <label className="flex items-center gap-2 text-sm text-stone-700 pb-1.5">
              <input
                type="checkbox"
                checked={addDraft.has_bore_water}
                onChange={(e) => setAddDraft({ ...addDraft, has_bore_water: e.target.checked })}
              />
              Has bore water pump
            </label>
            <button
              onClick={addBuilding}
              disabled={addSaving || !addDraft.name.trim()}
              className="bg-slate-800 text-white text-sm font-medium rounded px-3 py-1.5 disabled:opacity-50"
            >
              {addSaving ? "Adding…" : "Add"}
            </button>
          </div>
        </div>
      )}

      {buildings.length === 0 ? (
        <p className="text-sm text-stone-500">No buildings yet — add one to get started.</p>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            {buildings.map((b) => (
              <button
                key={b.id}
                onClick={() => setSelectedBuildingId(b.id)}
                className={
                  "text-sm font-medium rounded px-3 py-1.5 border " +
                  (b.id === selectedBuildingId
                    ? "bg-slate-800 text-white border-slate-800"
                    : "text-stone-700 border-stone-300 hover:border-stone-500")
                }
              >
                {b.name}
                {b.has_bore_water && <span className="ml-1 opacity-70">💧</span>}
              </button>
            ))}
          </div>

          {selectedBuilding && (
            <div className="bg-white border border-stone-300 rounded p-4">
              <div className="text-sm font-semibold text-slate-800 mb-3">
                {selectedBuilding.name} — Occupancy
              </div>

              {flatsError && (
                <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 mb-3">
                  {flatsError}
                </div>
              )}

              {flatsByNumber === null && !flatsError ? (
                <p className="text-sm text-stone-500">Loading flats…</p>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {FLOORS.map((floor) => (
                    <div key={floor} className="grid grid-cols-4 gap-1.5">
                      {UNITS.map((unit) => {
                        const flatNumber = floor * 100 + unit;
                        const flat = flatsByNumber[flatNumber];
                        const style = STATUS_STYLE[flat?.status || "unknown"];
                        return (
                          <button
                            key={flatNumber}
                            onClick={() => openFlatEditor(flatNumber)}
                            className="flex flex-col items-center gap-1 border border-stone-300 rounded bg-stone-50 hover:border-slate-500 py-2"
                          >
                            <span className="font-mono text-sm">{flatNumber}</span>
                            <span className={`text-[9px] font-semibold border rounded px-1.5 py-0.5 ${style.classes}`}>
                              {style.label}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {editingFlatNumber != null && (
        <div className="fixed inset-0 bg-stone-900/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded p-5 w-full max-w-sm border-t-4 border-amber-600 flex flex-col gap-3">
            <h3 className="font-semibold text-slate-800">
              {selectedBuilding?.name} · Flat {editingFlatNumber}
            </h3>

            {flatSaveError && (
              <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
                {flatSaveError}
              </div>
            )}

            <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
              Status
              <select
                value={flatStatusDraft}
                onChange={(e) => setFlatStatusDraft(e.target.value)}
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
              >
                <option value="unknown">Unset</option>
                <option value="owner">Owner-occupied</option>
                <option value="rented">Rented out</option>
                <option value="vacant">Vacant</option>
              </select>
            </label>

            <div className="flex gap-2 mt-1">
              <button
                onClick={saveFlatStatus}
                disabled={flatSaving}
                className="bg-slate-800 text-white text-sm font-medium rounded px-3 py-1.5 disabled:opacity-50"
              >
                {flatSaving ? "Saving…" : "Save"}
              </button>
              <button
                onClick={() => setEditingFlatNumber(null)}
                disabled={flatSaving}
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