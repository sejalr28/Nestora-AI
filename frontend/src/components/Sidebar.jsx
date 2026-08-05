import { NavLink } from "react-router-dom";

export const NAV_ITEMS = [
  { to: "/water-schedule", label: "Water Schedule" },
  { to: "/buildings", label: "Buildings" },
  { to: "/vendors", label: "Vendors" },
  { to: "/residents", label: "Residents" },
  { to: "/service-requests", label: "Service Requests" },
];

const LINK_BASE =
  "block px-4 py-2.5 rounded text-sm font-medium transition-colors";

/**
 * `onNavigate` is called after a link click -- on mobile this closes the
 * off-canvas drawer (passed down from DashboardLayout); on desktop it's a
 * no-op since there's nothing to close.
 */
export function Sidebar({ onNavigate }) {
  return (
    <nav className="flex flex-col gap-1 p-3">
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          onClick={onNavigate}
          className={({ isActive }) =>
            LINK_BASE +
            " " +
            (isActive
              ? "bg-slate-800 text-white"
              : "text-stone-700 hover:bg-stone-200")
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}