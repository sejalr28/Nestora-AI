import { Routes, Route, Navigate } from "react-router-dom";
import { DashboardLayout } from "./components/DashboardLayout";
import { ComingSoon } from "./components/ComingSoon";
import WaterSchedulePage from "./pages/WaterSchedulePage";
import BuildingsPage from "./pages/BuildingsPage";

/**
 * Route table. DashboardLayout renders the sidebar/top bar once and every
 * child route below renders into its <Outlet />. Water Schedule (Phase 3)
 * and Buildings (Phase 4) are now real pages; the rest stay ComingSoon
 * placeholders until their own phase builds them.
 */
export default function App() {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route index element={<Navigate to="/water-schedule" replace />} />
        <Route path="/water-schedule" element={<WaterSchedulePage />} />
        <Route path="/buildings" element={<BuildingsPage />} />
        <Route path="/vendors" element={<ComingSoon label="Vendors" phase={5} />} />
        <Route path="/residents" element={<ComingSoon label="Residents" phase={6} />} />
        <Route path="/service-requests" element={<ComingSoon label="Service Requests" phase={7} />} />
        <Route path="*" element={<ComingSoon label="Not found" phase="?" />} />
      </Route>
    </Routes>
  );
}