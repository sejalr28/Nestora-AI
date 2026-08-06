export function StatCard({ label, value, accentClass = "border-l-slate-800" }) {
  return (
    <div className={`bg-white border border-stone-300 border-l-4 ${accentClass} rounded p-4`}>
      <div className="text-[11px] uppercase tracking-wide text-stone-500 font-semibold">{label}</div>
      <div className="text-2xl font-semibold text-slate-800 mt-1">{value}</div>
    </div>
  );
}