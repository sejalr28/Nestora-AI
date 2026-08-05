import { Routes, Route, Navigate } from "react-router-dom";
import { DashboardLayout } from "./components/DashboardLayout";
import { ComingSoon } from "./components/ComingSoon";
import WaterSchedulePage from "./pages/WaterSchedulePage";
import BuildingsPage from "./pages/BuildingsPage";
import VendorsPage from "./pages/VendorsPage";
import ResidentsPage from "./pages/ResidentsPage";
import ServiceRequestsPage from "./pages/ServiceRequestsPage";

/**
 * Route table. DashboardLayout renders the sidebar/top bar once and every
 * child route below renders into its <Outlet />. All five sections are now
 * real pages (Phases 3-7). ComingSoon stays only for genuinely unknown
 * routes (the "*" fallback).
 */
export default function App() {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route index element={<Navigate to="/water-schedule" replace />} />
        <Route path="/water-schedule" element={<WaterSchedulePage />} />
        <Route path="/buildings" element={<BuildingsPage />} />
        <Route path="/vendors" element={<VendorsPage />} />
        <Route path="/residents" element={<ResidentsPage />} />
        <Route path="/service-requests" element={<ServiceRequestsPage />} />
        <Route path="*" element={<ComingSoon label="Not found" phase="?" />} />
      </Route>
    </Routes>
  );
}