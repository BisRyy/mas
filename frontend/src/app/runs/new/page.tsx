"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export default function NewRunPage() {
  const router = useRouter();
  const configs = useQuery({
    queryKey: ["configs"],
    queryFn: api.listConfigs,
  });

  const [configName, setConfigName] = useState<string>("");
  const [seedsText, setSeedsText] = useState<string>("1,2,3");
  const [overridesText, setOverridesText] = useState<string>("{}");
  const [error, setError] = useState<string>("");

  const create = useMutation({
    mutationFn: api.createRun,
    onSuccess: (job) => router.push(`/runs/${job.id}`),
    onError: (e: Error) => setError(e.message),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    let overrides: Record<string, unknown> = {};
    try {
      overrides = overridesText.trim() ? JSON.parse(overridesText) : {};
    } catch (err) {
      setError("Overrides must be valid JSON.");
      return;
    }
    const seeds = seedsText
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map((s) => Number(s));
    if (seeds.some((s) => Number.isNaN(s))) {
      setError("Seeds must be a comma-separated list of integers.");
      return;
    }
    if (!configName) {
      setError("Pick a config.");
      return;
    }
    create.mutate({ config_name: configName, seeds, overrides });
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Launch new run</h1>
        <p className="text-ink-muted">
          Spawn a fresh sweep on the server. Pick one of the YAML configs
          shipped in <code>experiments/configs/</code>, list the seeds you
          want to run (e.g. <code>1,2,3</code> or <code>101..110</code>), and
          optionally override any top-level YAML key from the config
          (e.g. <code>{"{\"lead_time\": 14}"}</code>) without editing the file.
        </p>
        <p className="text-xs text-ink-subtle">
          The job is enqueued (bounded by <code>MAS_MAX_QUEUED_RUNS</code>,
          executed by <code>MAS_MAX_CONCURRENT_RUNS</code> workers) and runs
          in the background. You&apos;ll be redirected to a live progress view
          where the log streams over WebSocket; results auto-ingest on
          completion and appear in <em>/experiments</em>.
        </p>
      </header>

      <form onSubmit={submit} className="card space-y-4">
        <div>
          <label className="metric-label">Config</label>
          <select
            value={configName}
            onChange={(e) => setConfigName(e.target.value)}
            className="mt-1 w-full rounded-md border border-border bg-bg-elevated px-3 py-2 text-sm text-ink"
          >
            <option value="">— select a config —</option>
            {configs.data?.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name}
                {c.policy ? ` (${c.policy})` : ""}
                {c.has_drift ? " · drift" : ""}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="metric-label">Seeds (comma-separated)</label>
          <input
            value={seedsText}
            onChange={(e) => setSeedsText(e.target.value)}
            className="mt-1 w-full rounded-md border border-border bg-bg-elevated px-3 py-2 text-sm text-ink font-mono"
          />
        </div>

        <div>
          <label className="metric-label">Overrides (JSON)</label>
          <textarea
            rows={4}
            value={overridesText}
            onChange={(e) => setOverridesText(e.target.value)}
            className="mt-1 w-full rounded-md border border-border bg-bg-elevated px-3 py-2 text-xs text-ink font-mono"
            placeholder='{"lead_time": 14, "service_level_z": 1.96}'
          />
        </div>

        {error && (
          <div className="rounded-md border border-rose-700 bg-rose-950/40 px-3 py-2 text-sm text-rose-300">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={create.isPending}
          className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-muted disabled:opacity-60"
        >
          {create.isPending ? "Submitting…" : "Submit run"}
        </button>
      </form>
    </div>
  );
}
