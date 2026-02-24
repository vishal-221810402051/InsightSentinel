import { NavLink } from "react-router-dom";

const linkBase =
  "flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition " +
  "hover:bg-slate-900/70 hover:text-slate-50";

const linkActive = "bg-slate-900/70 text-slate-50";
const linkInactive = "text-slate-300";

export default function Sidebar() {
  return (
    <aside className="w-64 shrink-0 border-r border-slate-800 bg-slate-950/60">
      <div className="p-4">
        <div className="rounded-2xl bg-slate-900/40 p-3">
          <div className="text-sm font-semibold tracking-wide">InsightSentinel</div>
          <div className="text-xs text-slate-400">Monitoring Console</div>
        </div>

        <nav className="mt-6 space-y-1">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `${linkBase} ${isActive ? linkActive : linkInactive}`
            }
            end
          >
            <span className="inline-block h-2 w-2 rounded-full bg-cyan-400" />
            Overview
          </NavLink>

          <NavLink
            to="/datasets/demo"
            className={({ isActive }) =>
              `${linkBase} ${isActive ? linkActive : linkInactive}`
            }
          >
            <span className="inline-block h-2 w-2 rounded-full bg-violet-400" />
            Dataset Detail
          </NavLink>
        </nav>
      </div>

      <div className="mt-auto p-4">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-3">
          <div className="text-xs text-slate-400">Backend</div>
          <div className="text-sm text-slate-200">localhost:8000</div>
        </div>
      </div>
    </aside>
  );
}
