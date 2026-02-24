import { useParams } from "react-router-dom";

import RiskBadge from "../components/RiskBadge";
import Topbar from "../components/Topbar";

export default function DatasetDetail() {
  const { id } = useParams();

  return (
    <>
      <Topbar
        title="Dataset Detail"
        subtitle={`Dataset: ${id}`}
        right={<RiskBadge level="moderate" />}
      />

      <div className="min-h-0 flex-1 overflow-auto p-6">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/20 p-4">
          <div className="text-sm font-semibold">Placeholder</div>
          <div className="mt-1 text-sm text-slate-300">
            Phase 7F-D will add charts (risk history, velocity, acceleration) +
            insights + alerts.
          </div>
        </div>
      </div>
    </>
  );
}
