import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { apiGet } from "../api/client";
import KPICard from "../components/KPICard";
import RiskBadge from "../components/RiskBadge";
import Topbar from "../components/Topbar";

type Dataset = {
  id: string;
  name: string;
  description?: string;
  row_count: number;
  column_count: number;
  created_at: string;
};

type DatasetsResponse = Dataset[] | { value?: Dataset[] };

type Risk = {
  dataset_risk_score: number;
  risk_level: string;
};

export default function Overview() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [riskMap, setRiskMap] = useState<Record<string, Risk>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const dsRes = await apiGet<DatasetsResponse>("/datasets");
        const ds = Array.isArray(dsRes) ? dsRes : dsRes.value ?? [];
        setDatasets(ds);

        const results = await Promise.allSettled(
          ds.map(async (d) => {
            const risk = await apiGet<Risk>(`/datasets/${d.id}/risk`);
            return [d.id, risk] as const;
          })
        );

        const nextRiskMap: Record<string, Risk> = {};
        for (const result of results) {
          if (result.status === "fulfilled") {
            const [id, risk] = result.value;
            nextRiskMap[id] = risk;
          }
        }
        setRiskMap(nextRiskMap);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  const rankedDatasets = useMemo(() => {
    return [...datasets].sort((a, b) => {
      const aScore = riskMap[a.id]?.dataset_risk_score ?? -1;
      const bScore = riskMap[b.id]?.dataset_risk_score ?? -1;
      return bScore - aScore;
    });
  }, [datasets, riskMap]);

  const highRiskCount = Object.values(riskMap).filter(
    (r) => r.risk_level === "high" || r.risk_level === "critical"
  ).length;

  return (
    <>
      <Topbar title="Overview" subtitle="Live portfolio snapshot" />

      <div className="flex-1 overflow-auto p-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <KPICard label="Datasets" value={datasets.length} />
          <KPICard label="High Risk" value={highRiskCount} />
          <KPICard label="Loaded Risks" value={Object.keys(riskMap).length} />
          <KPICard label="Mode" value="Monitoring" />
        </div>

        <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/30 p-4">
          <div className="mb-4 text-sm font-semibold">Datasets</div>

          {loading ? (
            <div className="text-sm text-slate-400">Loading...</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-slate-400">
                <tr>
                  <th className="pb-2 text-left">Name</th>
                  <th className="pb-2 text-left">Rows</th>
                  <th className="pb-2 text-left">Columns</th>
                  <th className="pb-2 text-left">Risk</th>
                  <th className="pb-2 text-left">Score</th>
                  <th className="pb-2 text-left">Action</th>
                </tr>
              </thead>
              <tbody>
                {rankedDatasets.map((d) => {
                  const risk = riskMap[d.id];
                  return (
                    <tr key={d.id} className="border-t border-slate-800">
                      <td className="py-2">{d.name}</td>
                      <td>{d.row_count}</td>
                      <td>{d.column_count}</td>
                      <td>
                        {risk ? (
                          <RiskBadge level={risk.risk_level} />
                        ) : (
                          <span className="text-xs text-slate-500">No risk</span>
                        )}
                      </td>
                      <td>{risk ? risk.dataset_risk_score : "-"}</td>
                      <td>
                        <Link
                          to={`/datasets/${d.id}`}
                          className="text-cyan-400 hover:underline"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}
