import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { buildingsApi } from "../api/buildings";
import { flatsApi } from "../api/flats";
import { residentsApi } from "../api/residents";
import { vendorsApi } from "../api/vendors";
import { serviceRequestsApi } from "../api/serviceRequests";
import { StatCard } from "../components/StatCard";
import { Skeleton } from "../components/Skeleton";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";

const QUICK_ACTIONS = [
  { to: "/buildings", label: "Add Building" },
  { to: "/residents", label: "Add Resident" },
  { to: "/service-requests", label: "Log Service Request" },
  { to: "/vendors", label: "Add Vendor" },
];

const REQUEST_STATUS_STYLE = {
  open: "border-amber-600 text-amber-700",
  assigned: "border-blue-600 text-blue-700",
  done: "border-emerald-600 text-emerald-700",
};

export default function DashboardHomePage() {
  const [data, setData] = useState(null); // aggregated stats + lists, null while loading
  const [error, setError] = useState(null);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setError(null);
    setData(null);
    try {
      const [buildings, residents, vendors, requests] = await Promise.all([
        buildingsApi.list(),
        residentsApi.list(),
        vendorsApi.list({ activeOnly: false }),
        serviceRequestsApi.list(), // no status filter -> all, already newest-first from the backend
      ]);

      // Flats have no "list all" endpoint (by design -- see flatsApi), so we
      // aggregate per building, same pattern ResidentsPage already uses.
      const flatsPerBuilding = await Promise.all(buildings.map((b) => flatsApi.listByBuilding(b.id)));
      const flats = flatsPerBuilding.flat();

      setData({ buildings, residents, vendors, requests, flats });
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) {
    return <ErrorState message={`Couldn't load the dashboard: ${error}`} onRetry={load} />;
  }

  if (data === null) {
    return <DashboardSkeleton />;
  }

  const { buildings, residents, vendors, requests, flats } = data;

  const occupiedFlats = flats.filter((f) => f.status === "owner" || f.status === "rented").length;
  const vacantFlats = flats.filter((f) => f.status === "vacant").length;
  const unsetFlats = flats.length - occupiedFlats - vacantFlats;
  const occupancyRate = flats.length > 0 ? Math.round((occupiedFlats / flats.length) * 100) : 0;

  const openRequests = requests.filter((r) => r.status === "open").length;
  const assignedRequests = requests.filter((r) => r.status === "assigned").length;
  const doneRequests = requests.filter((r) => r.status === "done").length;

  const activeVendors = vendors.filter((v) => v.is_active);
  const vendorsByCategory = activeVendors.reduce((acc, v) => {
    acc[v.category] = (acc[v.category] || 0) + 1;
    return acc;
  }, {});

  const recentRequests = requests.slice(0, 5);
  // Residents have no timestamp exposed by the API; the list is ordered by
  // ascending id, so the last N (reversed) is a reasonable "recently added"
  // proxy without needing a backend change.
  const recentResidents = residents.slice(-5).reverse();

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-lg font-semibold text-slate-800">Dashboard</h2>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Buildings" value={buildings.length} />
        <StatCard label="Flats" value={flats.length} />
        <StatCard label="Residents" value={residents.length} />
        <StatCard label="Open Requests" value={openRequests} accentClass="border-l-amber-600" />
        <StatCard label="Assigned Requests" value={assignedRequests} accentClass="border-l-blue-600" />
        <StatCard label="Active Vendors" value={activeVendors.length} accentClass="border-l-emerald-600" />
      </div>

      {/* Quick actions */}
      <div>
        <h3 className="text-sm font-semibold text-stone-600 mb-2">Quick actions</h3>
        <div className="flex flex-wrap gap-2">
          {QUICK_ACTIONS.map((action) => (
            <Link
              key={action.label}
              to={action.to}
              className="text-sm font-medium text-slate-800 border border-slate-800 rounded px-3 py-1.5 hover:bg-slate-800/5"
            >
              + {action.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Statistics */}
      <div>
        <h3 className="text-sm font-semibold text-stone-600 mb-2">Statistics</h3>
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="bg-white border border-stone-300 rounded p-4">
            <div className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-2">Occupancy</div>
            {flats.length === 0 ? (
              <EmptyState message="No flats recorded yet." />
            ) : (
              <>
                <div className="text-xl font-semibold text-slate-800">{occupancyRate}% occupied</div>
                <div className="text-sm text-stone-500 mt-1">
                  {occupiedFlats} occupied · {vacantFlats} vacant · {unsetFlats} unset
                </div>
              </>
            )}
          </div>

          <div className="bg-white border border-stone-300 rounded p-4">
            <div className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-2">
              Service request status
            </div>
            <div className="text-sm text-stone-700 flex flex-col gap-1">
              <span>Open: {openRequests}</span>
              <span>Assigned: {assignedRequests}</span>
              <span>Done: {doneRequests}</span>
            </div>
          </div>

          <div className="bg-white border border-stone-300 rounded p-4 sm:col-span-2">
            <div className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-2">
              Active vendors by category
            </div>
            {activeVendors.length === 0 ? (
              <EmptyState message="No active vendors yet — add one from the Vendors page." />
            ) : (
              <div className="flex flex-wrap gap-2">
                {Object.entries(vendorsByCategory).map(([category, count]) => (
                  <span
                    key={category}
                    className="text-sm text-stone-700 border border-stone-300 rounded px-2.5 py-1"
                  >
                    {category}: {count}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent activity */}
      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <h3 className="text-sm font-semibold text-stone-600 mb-2">Recent service requests</h3>
          {recentRequests.length === 0 ? (
            <EmptyState message="No requests logged yet." />
          ) : (
            <div className="flex flex-col gap-2">
              {recentRequests.map((r) => (
                <div key={r.id} className="bg-white border border-stone-300 rounded px-3 py-2 text-sm">
                  <span
                    className={`text-[10px] font-semibold uppercase tracking-wide border rounded px-1.5 py-0.5 mr-2 ${REQUEST_STATUS_STYLE[r.status]}`}
                  >
                    {r.status}
                  </span>
                  {r.category} · {r.flat.building.name}, Flat {r.flat.flat_number}
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <h3 className="text-sm font-semibold text-stone-600 mb-2">Recently added residents</h3>
          {recentResidents.length === 0 ? (
            <EmptyState message="No residents yet." />
          ) : (
            <div className="flex flex-col gap-2">
              {recentResidents.map((r) => (
                <div key={r.id} className="bg-white border border-stone-300 rounded px-3 py-2 text-sm">
                  {r.name || <span className="text-stone-400 italic">No name on file</span>}
                  <span className="text-stone-500"> · {r.phone_number}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true" aria-label="Loading dashboard">
      <Skeleton className="h-6 w-40" />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
      <Skeleton className="h-24" />
      <div className="grid sm:grid-cols-2 gap-4">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
    </div>
  );
}