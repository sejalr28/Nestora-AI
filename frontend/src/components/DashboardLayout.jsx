import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function DashboardLayout() {
    const [isSidebarOpen, setSidebarOpen] = useState(false);

    return (
        <div className="min-h-screen bg-stone-100 text-stone-900">
            <Topbar isSidebarOpen={isSidebarOpen} onToggleSidebar={() => setSidebarOpen((v) => !v)} />

            <div className="flex">
                {/* Desktop sidebar: always visible, part of the normal layout flow. */}
                <aside className="hidden md:block w-56 shrink-0 border-r border-stone-300 bg-white min-h-[calc(100vh-64px)]">
                    <Sidebar />
                </aside>

                {/* Mobile sidebar: off-canvas drawer + backdrop, only rendered when open. */}
                {isSidebarOpen && (
                    <div className="md:hidden fixed inset-0 z-40 flex">
                        <div
                            className="fixed inset-0 bg-stone-900/40"
                            onClick={() => setSidebarOpen(false)}
                            aria-hidden="true"
                        />
                        <aside className="relative w-64 max-w-[80vw] bg-white h-full shadow-xl">
                            <Sidebar onNavigate={() => setSidebarOpen(false)} />
                        </aside>
                    </div>
                )}

                <main className="flex-1 min-w-0 px-4 md:px-6 py-6">
                    <div className="max-w-4xl mx-auto">
                        <Outlet />
                    </div>
                </main>
            </div>
        </div>
    );
}