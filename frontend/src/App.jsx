import { Routes, Route } from "react-router-dom";

/**
 * Route table lives here. Right now there's just a placeholder at "/" to
 * confirm routing works end to end -- the real layout (sidebar/top nav)
 * and pages get wired in as nested routes in Phase 2 onward, replacing
 * this placeholder route by route.
 */
export default function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <div className="min-h-screen flex items-center justify-center bg-stone-100">
            <div className="text-center">
              <div className="text-sm uppercase tracking-wide text-stone-500 font-medium">
                SocietyBoard Admin
              </div>
              <h1 className="text-2xl font-semibold text-slate-800 mt-1">
                Frontend scaffold ready
              </h1>
              <p className="text-sm text-stone-500 mt-2">
                Tailwind, Axios, and React Router are wired up. Layout and pages come next.
              </p>
            </div>
          </div>
        }
      />
    </Routes>
  );
}