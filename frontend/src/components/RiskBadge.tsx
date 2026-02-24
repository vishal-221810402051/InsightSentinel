type Level = "low" | "moderate" | "high" | "critical" | string;

function cls(level: Level) {
  const base =
    "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium";

  if (level === "low")
    return `${base} border-emerald-800 bg-emerald-900/20 text-emerald-200`;

  if (level === "moderate")
    return `${base} border-amber-800 bg-amber-900/20 text-amber-200`;

  if (level === "high")
    return `${base} border-orange-800 bg-orange-900/20 text-orange-200`;

  if (level === "critical")
    return `${base} border-red-800 bg-red-900/20 text-red-200`;

  return `${base} border-slate-700 bg-slate-900/30 text-slate-200`;
}

export default function RiskBadge({ level }: { level: Level }) {
  return <span className={cls(level)}>{String(level).toUpperCase()}</span>;
}
