const MENU_ICON_PATHS = "M4 6h16M4 12h16M4 18h16";
const CLOSE_ICON_PATHS = "M6 18L18 6M6 6l12 12";

export function Topbar({ isSidebarOpen, onToggleSidebar }) {
  const today = new Date().toLocaleDateString("en-IN", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  return (
    <header className="bg-slate-800 text-stone-100 border-b-4 border-amber-600 px-4 md:px-6 py-3 flex items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="md:hidden p-1.5 rounded hover:bg-white/10"
          aria-label={isSidebarOpen ? "Close menu" : "Open menu"}
        >
          <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d={isSidebarOpen ? CLOSE_ICON_PATHS : MENU_ICON_PATHS} />
          </svg>
        </button>

        <div className="w-9 h-9 rounded-full border-2 border-amber-500 flex items-center justify-center font-bold text-amber-500 text-xs shrink-0">
          SB
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-wide opacity-75 leading-none">
            SocietyBoard Admin
          </div>
          <h1 className="text-lg md:text-xl font-semibold leading-tight">Committee Dashboard</h1>
        </div>
      </div>

      <div className="font-mono text-xs md:text-sm opacity-85 hidden sm:block">{today}</div>
    </header>
  );
}