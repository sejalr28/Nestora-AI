export function ComingSoon({ label, phase }) {
  return (
    <div className="bg-white border border-stone-300 border-l-4 border-l-amber-600 rounded p-6">
      <h2 className="text-lg font-semibold text-slate-800">{label}</h2>
      <p className="text-sm text-stone-500 mt-1">
        This page is built in Phase {phase} — the route and nav link are wired up now so you can
        confirm navigation works end to end.
      </p>
    </div>
  );
}