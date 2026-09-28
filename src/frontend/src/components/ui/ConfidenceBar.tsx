interface ConfidenceBarProps {
  value: number; // 0..1
}

function toneFor(value: number): { bar: string; text: string } {
  if (value >= 0.9) return { bar: "bg-red-500", text: "text-red-700 dark:text-red-400" };
  if (value >= 0.8) return { bar: "bg-amber-500", text: "text-amber-700 dark:text-amber-400" };
  return { bar: "bg-slate-400", text: "text-slate-600 dark:text-slate-400" };
}

export function ConfidenceBar({ value }: ConfidenceBarProps) {
  const pct = Math.round(value * 100);
  const { bar, text } = toneFor(value);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div className={`h-full rounded-full ${bar}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-sm font-semibold tabular-nums ${text}`}>{value.toFixed(2)}</span>
    </div>
  );
}
