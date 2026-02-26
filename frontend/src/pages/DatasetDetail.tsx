import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiGet, apiPost } from "../api/client";
import RiskBadge from "../components/RiskBadge";
import Topbar from "../components/Topbar";
import {
  demoAlerts,
  demoDataset,
  demoInsights,
  demoRisk,
  demoRiskHistory,
} from "../data/demoDataset";

type Dataset = {
  id: string;
  name: string;
  description?: string;
  row_count: number;
  column_count: number;
  created_at: string;
};

type Risk = {
  dataset_risk_score: number;
  risk_level: string;
  smoothed_score?: number | null;
  alpha_used?: number | null;
  delta_score?: number | null;
  accel_score?: number | null;
};

type RiskHistoryItem = {
  id?: string;
  risk_score: number;
  risk_level: string;
  smoothed_score?: number | null;
  alpha_used?: number | null;
  delta_score?: number | null;
  accel_score?: number | null;
  created_at: string;
};

type RiskHistoryResponse = {
  history?: RiskHistoryItem[];
  value?: RiskHistoryItem[];
};

type Insight = {
  code: string;
  severity: string;
  title: string;
  message?: string;
};

type InsightsResponse = {
  insights?: Insight[];
  value?: Insight[];
};

type AlertEvent = {
  severity: string;
  title: string;
  message?: string;
  created_at: string;
};

const isUuid = (s: string) =>
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    s
  );

function formatDate(value?: string) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function toShortTime(value?: string) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatSigned(value: number | null) {
  if (value === null || Number.isNaN(value)) return "-";
  return value > 0 ? `+${value}` : `${value}`;
}

function formatFixed(value: number | null, digits = 3) {
  if (value === null || Number.isNaN(value)) return "-";
  return value.toFixed(digits);
}

function computeDeltaAndAccel(history: RiskHistoryItem[]) {
  // History can arrive newest-first; chart and trend math use chronological order.
  const sorted = [...history].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );

  const n = sorted.length;
  const last = n >= 1 ? sorted[n - 1].risk_score : null;
  const prev = n >= 2 ? sorted[n - 2].risk_score : null;
  const prev2 = n >= 3 ? sorted[n - 3].risk_score : null;

  const delta = last !== null && prev !== null ? last - prev : null;
  const prevDelta = prev !== null && prev2 !== null ? prev - prev2 : null;
  const accel = delta !== null && prevDelta !== null ? delta - prevDelta : null;

  return { sorted, last, delta, accel };
}

const TRACK_COOLDOWN_MS = 1200;

function LoadingState() {
  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="text-slate-400">Loading...</div>
    </div>
  );
}

export default function DatasetDetail() {
  const { id = "" } = useParams();
  const navigate = useNavigate();

  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [risk, setRisk] = useState<Risk | null>(null);
  const [riskHistory, setRiskHistory] = useState<RiskHistoryItem[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [isTracking, setIsTracking] = useState(false);
  const [trackCooldownUntil, setTrackCooldownUntil] = useState<number>(0);
  const trackCooldownTimerRef = useRef<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { sorted: riskSeries, last: lastScore, delta, accel } =
    computeDeltaAndAccel(riskHistory);
  const chartData = riskSeries.map((h) => ({
    t: toShortTime(h.created_at),
    score: h.risk_score,
  }));
  const latestHistoryPoint =
    riskSeries.length > 0 ? riskSeries[riskSeries.length - 1] : null;
  const displayDelta = risk?.delta_score ?? latestHistoryPoint?.delta_score ?? delta;
  const displayAccel = risk?.accel_score ?? latestHistoryPoint?.accel_score ?? accel;
  const displaySmoothed =
    risk?.smoothed_score ?? latestHistoryPoint?.smoothed_score ?? null;
  const displayAlpha = risk?.alpha_used ?? latestHistoryPoint?.alpha_used ?? null;

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      if (id === "demo") {
        if (cancelled) return;
        setDataset(demoDataset);
        setRisk(demoRisk);
        setRiskHistory(demoRiskHistory);
        setInsights(demoInsights);
        setAlerts(demoAlerts);
        setLoading(false);
        return;
      }

      if (!isUuid(id)) {
        if (cancelled) return;
        setError("Dataset not found");
        setLoading(false);
        return;
      }

      try {
        const [ds, riskRes, historyRes, insightsRes, alertsRes] = await Promise.all([
          apiGet<Dataset>(`/datasets/${id}`),
          apiGet<Risk>(`/datasets/${id}/risk`),
          apiGet<RiskHistoryResponse>(`/datasets/${id}/risk/history?limit=25`),
          apiGet<InsightsResponse>(`/datasets/${id}/insights?refresh=false`),
          apiGet<AlertEvent[] | { value?: AlertEvent[] }>(
            `/datasets/${id}/alerts/events?limit=25`
          ),
        ]);

        if (cancelled) return;

        setDataset(ds);
        setRisk(riskRes);
        setRiskHistory(historyRes.history ?? historyRes.value ?? []);
        setInsights(insightsRes.insights ?? insightsRes.value ?? []);
        setAlerts(Array.isArray(alertsRes) ? alertsRes : alertsRes.value ?? []);
        setLoading(false);
      } catch (e) {
        if (cancelled) return;
        console.error(e);
        setError("Dataset not found");
        setLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    return () => {
      if (trackCooldownTimerRef.current !== null) {
        window.clearTimeout(trackCooldownTimerRef.current);
      }
    };
  }, []);

  async function onTrackNow() {
    const now = Date.now();
    if (!isUuid(id)) return;
    if (isTracking) return;
    if (now < trackCooldownUntil) return;

    setIsTracking(true);
    setTrackCooldownUntil(now + TRACK_COOLDOWN_MS);
    if (trackCooldownTimerRef.current !== null) {
      window.clearTimeout(trackCooldownTimerRef.current);
    }
    trackCooldownTimerRef.current = window.setTimeout(() => {
      setTrackCooldownUntil(0);
      trackCooldownTimerRef.current = null;
    }, TRACK_COOLDOWN_MS);

    setError(null);
    try {
      await apiPost(`/datasets/${id}/risk/track`);
      const [riskRes, historyRes, insightsRes, alertsRes] = await Promise.all([
        apiGet<Risk>(`/datasets/${id}/risk`),
        apiGet<RiskHistoryResponse>(`/datasets/${id}/risk/history?limit=25`),
        apiGet<InsightsResponse>(`/datasets/${id}/insights?refresh=false`),
        apiGet<AlertEvent[] | { value?: AlertEvent[] }>(
          `/datasets/${id}/alerts/events?limit=25`
        ),
      ]);
      setRisk(riskRes);
      setRiskHistory(historyRes.history ?? historyRes.value ?? []);
      setInsights(insightsRes.insights ?? insightsRes.value ?? []);
      setAlerts(Array.isArray(alertsRes) ? alertsRes : alertsRes.value ?? []);
    } catch (e) {
      console.error(e);
      setError("Risk tracking failed.");
    } finally {
      setIsTracking(false);
    }
  }

  if (loading) {
    return <LoadingState />;
  }

  if (error) {
    return (
      <div className="flex-1 overflow-auto p-6">
        <div className="text-xl font-semibold">Dataset not found</div>
        <div className="mt-2 text-sm text-slate-400">
          The dataset id is invalid, or it no longer exists.
        </div>
        <button
          type="button"
          className="mt-6 rounded-lg border border-slate-700 px-4 py-2 hover:bg-white/5"
          onClick={() => navigate("/")}
        >
          Back to Overview
        </button>
      </div>
    );
  }

  return (
    <>
      <Topbar
        title={dataset?.name || "Dataset"}
        subtitle={`ID: ${id}`}
        right={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onTrackNow}
              disabled={isTracking || Date.now() < trackCooldownUntil || !isUuid(id)}
              className="rounded-xl border border-cyan-700 bg-cyan-900/30 px-3 py-2 text-xs text-cyan-200 hover:bg-cyan-900/50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isTracking ? "Tracking..." : "Track Now"}
            </button>
            {risk ? <RiskBadge level={risk.risk_level} /> : null}
          </div>
        }
      />

      <div className="flex-1 space-y-6 overflow-auto p-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <div className="card">
            <div className="label">Rows</div>
            <div className="value">{dataset?.row_count ?? "-"}</div>
          </div>
          <div className="card">
            <div className="label">Columns</div>
            <div className="value">{dataset?.column_count ?? "-"}</div>
          </div>
          <div className="card">
            <div className="label">Risk Score</div>
            <div className="value">{risk?.dataset_risk_score ?? "-"}</div>
          </div>
          <div className="card">
            <div className="label">Risk Level</div>
            <div className="value">{risk?.risk_level ?? "-"}</div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold">Risk Intelligence</div>
            <div className="flex items-center gap-3 text-xs text-slate-400">
              <span>
                Delta:{" "}
                <span className="text-slate-200">
                  {formatSigned(displayDelta)}
                </span>
              </span>
              <span>
                accel:{" "}
                <span className="text-slate-200">
                  {formatSigned(displayAccel)}
                </span>
              </span>
              <span>
                smooth:{" "}
                <span className="text-slate-200">
                  {displaySmoothed === null ? "-" : displaySmoothed}
                </span>
              </span>
              <span>
                alpha: <span className="text-slate-200">{formatFixed(displayAlpha, 3)}</span>
              </span>
            </div>
          </div>

          {chartData.length < 2 ? (
            <div className="text-sm text-slate-400">
              Not enough history for a trend line yet. Click <b>Track Now</b> a few
              times.
            </div>
          ) : (
            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={chartData}
                  margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="t" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} domain={["auto", "auto"]} />
                  <Tooltip />
                  <Line type="monotone" dataKey="score" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
            <div className="card">
              <div className="label">Latest score</div>
              <div className="value">{lastScore ?? "-"}</div>
            </div>
            <div className="card">
              <div className="label">Delta (last step)</div>
              <div className="value">{formatSigned(displayDelta)}</div>
            </div>
            <div className="card">
              <div className="label">Acceleration</div>
              <div className="value">{formatSigned(displayAccel)}</div>
            </div>
          </div>

          <div className="mt-4">
            <div className="mb-2 text-sm font-semibold">Risk History</div>
            {riskHistory.length === 0 ? (
              <div className="text-sm text-slate-400">No risk history</div>
            ) : (
              <ul className="space-y-2">
                {[...riskHistory].slice(0, 12).map((h, idx) => (
                  <li
                    key={h.id ?? `${h.created_at}-${idx}`}
                    className="flex items-center justify-between rounded-lg border border-slate-800 px-3 py-2 text-sm"
                  >
                    <span className="text-slate-300">{formatDate(h.created_at)}</span>
                    <span className="text-slate-100">score {h.risk_score}</span>
                    <RiskBadge level={h.risk_level} />
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-4">
          <div className="mb-3 text-sm font-semibold">Insights</div>
          {insights.length === 0 ? (
            <div className="text-sm text-slate-400">No insights</div>
          ) : (
            <ul className="space-y-2">
              {insights.map((insight, idx) => (
                <li key={`${insight.code}-${idx}`} className="text-sm">
                  <span className="mr-2 text-slate-400">[{insight.severity}]</span>
                  {insight.title}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-4">
          <div className="mb-3 text-sm font-semibold">Recent Alerts</div>
          {alerts.length === 0 ? (
            <div className="text-sm text-slate-400">No alerts</div>
          ) : (
            <ul className="space-y-2">
              {alerts.map((alert, idx) => (
                <li key={`${alert.title}-${alert.created_at}-${idx}`} className="text-sm">
                  <span className="mr-2 text-slate-400">[{alert.severity}]</span>
                  <span>{alert.title}</span>
                  <span className="ml-2 text-xs text-slate-500">
                    {formatDate(alert.created_at)}
                  </span>
                  {alert.message ? (
                    <div className="mt-1 text-xs text-slate-400">{alert.message}</div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </>
  );
}
