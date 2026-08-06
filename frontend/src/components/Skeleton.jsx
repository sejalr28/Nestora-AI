export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse bg-stone-200 rounded ${className}`} aria-hidden="true" />;
}