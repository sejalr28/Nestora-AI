import { useEffect, useState } from "react";
import { vendorsApi } from "../api/vendors";

const CATEGORIES = ["Plumber", "Electrician", "Carpenter", "Pest Control"];

export default function VendorsPage() {
  const [vendors, setVendors] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [showInactive, setShowInactive] = useState(false);

  const [showAddForm, setShowAddForm] = useState(false);
  const [addDraft, setAddDraft] = useState({ name: "", category: CATEGORIES[0], phone_number: "" });
  const [addError, setAddError] = useState(null);
  const [addSaving, setAddSaving] = useState(false);

  const [togglingId, setTogglingId] = useState(null);
  const [toggleError, setToggleError] = useState(null);

  useEffect(() => {
    load();
  }, [categoryFilter, showInactive]);

  async function load() {
    setLoadError(null);
    try {
      const data = await vendorsApi.list({ category: categoryFilter, activeOnly: !showInactive });
      setVendors(data);
    } catch (err) {
      setLoadError(err.message);
    }
  }

  async function addVendor() {
    if (!addDraft.name.trim() || !addDraft.phone_number.trim()) return;
    setAddSaving(true);
    setAddError(null);
    try {
      await vendorsApi.create(addDraft);
      setShowAddForm(false);
      setAddDraft({ name: "", category: CATEGORIES[0], phone_number: "" });
      await load();
    } catch (err) {
      setAddError(err.message);
    } finally {
      setAddSaving(false);
    }
  }

  async function toggleActive(vendor) {
    setTogglingId(vendor.id);
    setToggleError(null);
    try {
      await vendorsApi.update(vendor.id, { is_active: !vendor.is_active });
      await load();
    } catch (err) {
      setToggleError(err.message);
    } finally {
      setTogglingId(null);
    }
  }

  if (vendors === null && !loadError) {
    return <p className="text-sm text-stone-500">Loading…</p>;
  }

  if (loadError) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded px-4 py-3 flex items-center justify-between gap-3">
        <span>Couldn't load vendors: {loadError}</span>
        <button onClick={load} className="font-medium underline shrink-0">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-lg font-semibold text-slate-800">Vendors</h2>
        <button
          onClick={() => setShowAddForm((v) => !v)}
          className="text-sm font-medium text-slate-800 border border-slate-800 rounded px-3 py-1.5 hover:bg-slate-800/5"
        >
          + Add vendor
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
            <label className="flex-1 min-w-[160px] text-xs text-stone-500 font-medium flex flex-col gap-1">
              Name
              <input
                type="text"
                value={addDraft.name}
                onChange={(e) => setAddDraft({ ...addDraft, name: e.target.value })}
                placeholder="e.g. Ganesh Pipe Works"
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
              />
            </label>
            <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
              Category
              <select
                value={addDraft.category}
                onChange={(e) => setAddDraft({ ...addDraft, category: e.target.value })}
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
              >
                {CATEGORIES.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <label className="flex-1 min-w-[140px] text-xs text-stone-500 font-medium flex flex-col gap-1">
              Phone number
              <input
                type="text"
                value={addDraft.phone_number}
                onChange={(e) => setAddDraft({ ...addDraft, phone_number: e.target.value })}
                placeholder="e.g. 98221 04455"
                className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
              />
            </label>
            <button
              onClick={addVendor}
              disabled={addSaving || !addDraft.name.trim() || !addDraft.phone_number.trim()}
              className="bg-slate-800 text-white text-sm font-medium rounded px-3 py-1.5 disabled:opacity-50"
            >
              {addSaving ? "Adding…" : "Add"}
            </button>
          </div>
        </div>
      )}

      <div className="flex items-center gap-4 flex-wrap">
        <label className="text-xs text-stone-500 font-medium flex flex-col gap-1">
          Filter by category
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="border border-stone-400 rounded px-2 py-1.5 text-sm text-stone-900"
          >
            <option value="">All categories</option>
            {CATEGORIES.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm text-stone-700">
          <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />
          Show inactive vendors
        </label>
      </div>

      {toggleError && (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {toggleError}
        </div>
      )}

      {vendors.length === 0 ? (
        <p className="text-sm text-stone-500">No vendors match this filter.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {vendors.map((vendor) => (
            <div
              key={vendor.id}
              className="bg-white border border-stone-300 border-l-4 border-l-slate-800 rounded px-4 py-3 flex items-center justify-between gap-3 flex-wrap"
            >
              <div>
                <div className="font-medium text-stone-900">
                  {vendor.name}
                  {!vendor.is_active && (
                    <span className="ml-2 text-[10px] font-semibold uppercase tracking-wide text-stone-500 border border-stone-400 rounded px-1.5 py-0.5">
                      Inactive
                    </span>
                  )}
                </div>
                <div className="text-sm text-stone-500">
                  {vendor.category} · <a href={`tel:${vendor.phone_number}`} className="hover:underline">{vendor.phone_number}</a>
                </div>
              </div>
              <button
                onClick={() => toggleActive(vendor)}
                disabled={togglingId === vendor.id}
                className="text-sm font-medium text-slate-800 border border-slate-800 rounded px-3 py-1.5 disabled:opacity-50 shrink-0"
              >
                {togglingId === vendor.id ? "Saving…" : vendor.is_active ? "Deactivate" : "Activate"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}