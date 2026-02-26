export const demoDataset = {
  id: "demo",
  name: "Demo Dataset",
  row_count: 6000,
  column_count: 12,
  created_at: "2026-02-24T14:00:00Z",
  description: "Safe demo mode payload",
};

export const demoRisk = {
  dataset_risk_score: 42,
  risk_level: "moderate",
};

export const demoRiskHistory = [
  { created_at: "2026-02-24T10:00:00Z", risk_score: 18, risk_level: "low" },
  { created_at: "2026-02-24T12:00:00Z", risk_score: 26, risk_level: "moderate" },
  { created_at: "2026-02-24T14:00:00Z", risk_score: 42, risk_level: "moderate" },
];

export const demoInsights = [
  { severity: "warning", code: "SKEWED_DISTRIBUTION", title: "Skewed distribution" },
  { severity: "warning", code: "HIGH_NULL_RATIO", title: "High missing values" },
  { severity: "info", code: "LOW_CARDINALITY", title: "Low cardinality" },
];

export const demoAlerts = [
  { severity: "warning", title: "Risk spike detected", created_at: "2026-02-24T14:05:00Z" },
  { severity: "warning", title: "Outlier ratio rising", created_at: "2026-02-24T13:10:00Z" },
];
