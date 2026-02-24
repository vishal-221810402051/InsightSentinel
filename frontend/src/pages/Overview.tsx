import KPICard from "../components/KPICard";
import Topbar from "../components/Topbar";

export default function Overview() {
  return (
    <>
      <Topbar
        title="Overview"
        subtitle="Portfolio snapshot (Phase 7F-A layout shell)"
      />

      <div className="min-h-0 flex-1 overflow-auto p-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <KPICard label="Datasets" value="-" hint="7F-B will populate" />
          <KPICard label="High risk" value="-" hint="7F-C risk ranking" />
          <KPICard label="Alerts (24h)" value="-" hint="7F-D details" />
          <KPICard label="Acceleration" value="-" hint="7B signals" />
        </div>

        <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/20 p-4">
          <div className="text-sm font-semibold">Next</div>
          <div className="mt-1 text-sm text-slate-300">
            Phase 7F-B adds{" "}
            <code className="rounded bg-slate-900/60 px-1">/datasets/portfolio</code>{" "}
            so we can render a ranked table here with risk + trend signals.
          </div>
        </div>
      </div>
    </>
  );
}
