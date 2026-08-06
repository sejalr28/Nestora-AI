export function ErrorState({ message, onRetry }) {
  return (
    <div
      role="alert"
      className="bg-red-50 border border-red-200 text-red-700 text-sm rounded px-4 py-3 flex items-center justify-between gap-3"
    >
      <span>{message}</span>
      {onRetry && (
        <button onClick={onRetry} className="font-medium underline shrink-0">
          Retry
        </button>
      )}
    </div>
  );
}