import { Routes, Route } from "react-router-dom";
import { DashboardLayout } from "./components/DashboardLayout";
import { ComingSoon } from "./components/ComingSoon";
import DashboardHomePage from "./pages/DashboardHomePage";
import WaterSchedulePage from "./pages/WaterSchedulePage";
import BuildingsPage from "./pages/BuildingsPage";
import VendorsPage from "./pages/VendorsPage";
import ResidentsPage from "./pages/ResidentsPage";
import ServiceRequestsPage from "./pages/ServiceRequestsPage";

/**
 * Route table. DashboardLayout renders the sidebar/top bar once and every
 * child route below renders into its <Outlet />. "/" is now the real
 * Dashboard Home (Phase 8) instead of redirecting to Water Schedule.
 * ComingSoon stays only for genuinely unknown routes (the "*" fallback).
 */
export default function App() {
    return (
        <Routes>
            <Route element={<DashboardLayout />}>
                <Route index element={<DashboardHomePage />} />
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