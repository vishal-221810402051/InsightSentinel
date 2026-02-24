import type { ReactNode } from "react";

type Props = {
  title: string;
  subtitle?: string;
  right?: ReactNode;
};

export default function Topbar({ title, subtitle, right }: Props) {
  return (
    <header className="flex items-center justify-between gap-3 border-b border-slate-800 bg-slate-950/40 px-6 py-4 backdrop-blur">
      <div>
        <div className="text-lg font-semibold">{title}</div>
        {subtitle ? <div className="text-xs text-slate-400">{subtitle}</div> : null}
      </div>

      <div className="flex items-center gap-2">
        {right}
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-2 text-xs text-slate-200 hover:bg-slate-900/70"
        >
          API Docs
        </a>
      </div>
    </header>
  );
}
