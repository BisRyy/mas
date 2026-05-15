/**
 * Typed API client wrapping the FastAPI backend.
 *
 * All requests go through the Next.js rewrite at `/api/*` (configured in
 * next.config.ts), so this file uses bare relative paths.
 */

import { z } from "zod";

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------
export const ExperimentSummarySchema = z.object({
  id: z.number(),
  config_name: z.string(),
  scenario: z.string(),
  policy: z.string(),
  family: z.string(),
  n_seeds: z.number(),
  mean_stockout_rate: z.number().nullable(),
  mean_total_cost: z.number().nullable(),
  mean_n_orders: z.number().nullable(),
  mean_forecast_mape: z.number().nullable(),
  mean_runtime_seconds: z.number().nullable(),
  mean_n_drift_events: z.number().nullable(),
  ci95_stockout_lo: z.number().nullable(),
  ci95_stockout_hi: z.number().nullable(),
  drift_start_step: z.number().nullable(),
  updated_at: z.string(),
});
export type ExperimentSummary = z.infer<typeof ExperimentSummarySchema>;

export const ExperimentDetailSchema = ExperimentSummarySchema.extend({
  aggregate_json: z.unknown().nullable(),
  created_at: z.string(),
});
export type ExperimentDetail = z.infer<typeof ExperimentDetailSchema>;

export const SeedSummarySchema = z.object({
  id: z.number(),
  experiment_id: z.number(),
  seed_num: z.number(),
  n_skus: z.number().nullable(),
  stockout_rate: z.number().nullable(),
  total_cost: z.number().nullable(),
  n_orders: z.number().nullable(),
  forecast_mape: z.number().nullable(),
  runtime_seconds: z.number().nullable(),
  n_drift_events: z.number().nullable(),
  n_global_drift_events: z.number().nullable(),
  n_refits: z.number().nullable(),
});
export type SeedSummary = z.infer<typeof SeedSummarySchema>;

export const SeedDetailSchema = SeedSummarySchema.extend({
  summary_json: z.record(z.string(), z.unknown()).nullable(),
  timeseries_path: z.string().nullable(),
  peak_memory_mb: z.number().nullable(),
});
export type SeedDetail = z.infer<typeof SeedDetailSchema>;

export const TimeseriesPointSchema = z.object({
  step: z.number(),
  total_on_hand: z.number(),
  stockout_skus_step: z.number(),
});
export const SeedTimeseriesSchema = z.object({
  seed_id: z.number(),
  steps: z.array(TimeseriesPointSchema),
});
export type SeedTimeseries = z.infer<typeof SeedTimeseriesSchema>;

export const DecisionEntrySchema = z.object({
  id: z.number(),
  step: z.number(),
  agent: z.string(),
  action: z.string(),
  sku: z.string().nullable(),
  details_json: z.record(z.string(), z.unknown()).nullable(),
});
export const DecisionPageSchema = z.object({
  items: z.array(DecisionEntrySchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
});
export type DecisionPage = z.infer<typeof DecisionPageSchema>;

export const SystemStatusSchema = z.object({
  api: z.object({
    version: z.string(),
    uptime_seconds: z.number(),
    process_started_at_unix: z.number(),
  }),
  database: z.object({
    url_redacted: z.string(),
    counts: z.object({
      experiments: z.number(),
      seeds: z.number(),
      decisions: z.number(),
      jobs: z.number(),
    }),
    last_ingest_at: z.string().nullable(),
  }),
  filesystem: z.object({
    project_root: z.string(),
    results_dir: z.string(),
    results_size_bytes: z.number(),
    configs_dir: z.string(),
  }),
  queue: z.object({
    current_jobs: z.number(),
    max_queued: z.number(),
    max_concurrent: z.number(),
  }),
  policy: z.object({
    allow_run_launch: z.boolean(),
    cors_origins: z.array(z.string()),
  }),
});
export type SystemStatus = z.infer<typeof SystemStatusSchema>;

export const ReingestResultSchema = z.object({
  ok: z.boolean(),
  experiments: z.number(),
  seeds: z.number(),
  decisions: z.number(),
});

export const JobStatusSchema = z.object({
  id: z.string(),
  config_name: z.string(),
  seeds_csv: z.string(),
  status: z.string(),
  progress_pct: z.number(),
  completed_seeds: z.number(),
  total_seeds: z.number(),
  log_tail: z.string().nullable(),
  error: z.string().nullable(),
  overrides_json: z.record(z.string(), z.unknown()).nullable(),
  created_at: z.string(),
  started_at: z.string().nullable(),
  finished_at: z.string().nullable(),
});
export type JobStatus = z.infer<typeof JobStatusSchema>;

// ---------------------------------------------------------------------------
// Fetcher
// ---------------------------------------------------------------------------
async function http<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(path, {
    cache: "no-store",
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = body?.detail ?? "";
    } catch {}
    throw new Error(
      `${init?.method ?? "GET"} ${path} failed: ${res.status} ${detail}`,
    );
  }
  const data = await res.json();
  return schema.parse(data);
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------
export const api = {
  health: () => http("/api/health", z.object({ status: z.string(), version: z.string() })),

  // Experiments
  listExperiments: (params: {
    family?: string;
    scenario?: string;
    policy?: string;
    sort?: string;
    descending?: boolean;
    limit?: number;
  } = {}) => {
    const qs = new URLSearchParams();
    if (params.family) qs.set("family", params.family);
    if (params.scenario) qs.set("scenario", params.scenario);
    if (params.policy) qs.set("policy", params.policy);
    if (params.sort) qs.set("sort", params.sort);
    if (params.descending) qs.set("descending", "true");
    if (params.limit) qs.set("limit", String(params.limit));
    const path = `/api/experiments${qs.size ? `?${qs}` : ""}`;
    return http(path, z.array(ExperimentSummarySchema));
  },

  getExperiment: (name: string) =>
    http(`/api/experiments/${encodeURIComponent(name)}`, ExperimentDetailSchema),

  familyBreakdown: () =>
    http("/api/experiments/_stats/families", z.record(z.string(), z.number())),

  // Seeds
  listSeeds: (expName: string) =>
    http(`/api/experiments/${encodeURIComponent(expName)}/seeds`,
         z.array(SeedSummarySchema)),

  getSeed: (expName: string, seedNum: number) =>
    http(`/api/experiments/${encodeURIComponent(expName)}/seeds/${seedNum}`,
         SeedDetailSchema),

  getSeedTimeseries: (expName: string, seedNum: number) =>
    http(`/api/experiments/${encodeURIComponent(expName)}/seeds/${seedNum}/timeseries`,
         SeedTimeseriesSchema),

  // Decisions
  getDecisions: (expName: string, seedNum: number, params: {
    agent?: string; action?: string; sku?: string;
    step_min?: number; step_max?: number;
    page?: number; page_size?: number;
  } = {}) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== "") qs.set(k, String(v));
    }
    return http(
      `/api/experiments/${encodeURIComponent(expName)}/seeds/${seedNum}/decisions${qs.size ? `?${qs}` : ""}`,
      DecisionPageSchema,
    );
  },

  listSkusWithDecisions: (expName: string, seedNum: number) =>
    http(
      `/api/experiments/${encodeURIComponent(expName)}/seeds/${seedNum}/decisions/skus`,
      z.array(z.object({ sku: z.string(), decisions: z.number() })),
    ),

  listDecisionAgents: (expName: string, seedNum: number) =>
    http(
      `/api/experiments/${encodeURIComponent(expName)}/seeds/${seedNum}/decisions/agents`,
      z.array(z.object({ agent: z.string(), action: z.string(), count: z.number() })),
    ),

  // Reports
  h1Report: () => http("/api/reports/h1", z.object({
    generated_at: z.string(),
    tests: z.array(z.object({
      scenario: z.string(),
      baseline: z.string(),
      metric: z.string(),
      treatment_mean: z.number().nullable(),
      baseline_mean: z.number().nullable(),
      rel_change: z.number().nullable(),
      mannwhitney_p: z.number().nullable(),
      welch_p: z.number().nullable(),
      cohens_d: z.number().nullable(),
    })),
  })),

  h3Report: () => http("/api/reports/h3", z.object({
    generated_at: z.string(),
    fits: z.array(z.object({
      policy: z.string(),
      exponent_b: z.number(),
      a: z.number(),
      r2: z.number(),
      classification: z.string(),
      linear_r2: z.number().nullable(),
      raw_points: z.array(z.record(z.string(), z.unknown())),
    })),
  })),

  ablationReport: () => http("/api/reports/ablation", z.object({
    generated_at: z.string(),
    rows: z.array(z.object({
      variant: z.string(),
      n_seeds: z.number(),
      stockout_rate_mean: z.number().nullable(),
      total_cost_mean: z.number().nullable(),
      forecast_mape_mean: z.number().nullable(),
      n_global_drift_events_mean: z.number().nullable(),
      rel_to_full_stockout: z.number().nullable(),
      rel_to_full_cost: z.number().nullable(),
    })),
  })),

  // Configs (for the launcher)
  listConfigs: () => http("/api/configs", z.array(z.object({
    name: z.string(),
    scenario: z.string().nullable().optional(),
    policy: z.string().nullable().optional(),
    n_steps: z.number().nullable().optional(),
    fit_window: z.number().nullable().optional(),
    lead_time: z.number().nullable().optional(),
    has_drift: z.boolean(),
    size_bytes: z.number(),
  }))),

  // Runs
  listRuns: () => http("/api/runs", z.array(JobStatusSchema)),

  getRun: (jobId: string) =>
    http(`/api/runs/${jobId}`, JobStatusSchema),

  createRun: (payload: { config_name: string; seeds: number[]; overrides?: Record<string, unknown> }) =>
    http("/api/runs", JobStatusSchema, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Meta / diagnostics
  systemStatus: () => http("/api/_meta/status", SystemStatusSchema),
  reingest: () =>
    http("/api/_meta/reingest", ReingestResultSchema, { method: "POST" }),
};
