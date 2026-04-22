"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { policyLabel } from "@/lib/format";

export default function DecisionsIndexPage() {
  const all = useQuery({
    queryKey: ["experiments-for-decisions"],
    queryFn: () => api.listExperiments({ family: "h1", limit: 50 }),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">Decision audit</h1>
        <p className="text-ink-muted">
          Trace every recorded agent action. Pick an experiment + seed to see
          the per-step, per-SKU decision log.
        </p>
      </header>

      <div className="card overflow-hidden p-0">
        <table>
          <thead>
            <tr>
              <th>Experiment</th>
              <th>Policy</th>
              <th>Scenario</th>
              <th>Seeds available</th>
              <th>Open</th>
            </tr>
          </thead>
          <tbody>
            {all.data?.map((e) => (
              <tr key={e.id}>
                <td>
                  <Link href={`/decisions/${e.config_name}/1`} className="font-mono">
                    {e.config_name}
                  </Link>
                </td>
                <td>
                  <span className={`policy-dot ${e.policy}`} />
                  {policyLabel(e.policy)}
                </td>
                <td className="text-xs text-ink-muted">{e.scenario}</td>
                <td>{e.n_seeds}</td>
                <td>
                  <Link href={`/decisions/${e.config_name}/1`} className="text-sm">
                    Open seed 1 →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card text-sm text-ink-muted">
        Decision-log audit data is emitted by the simulator when the
        <code className="mx-1 font-mono">MAS_EMIT_DECISIONS=1</code>
        environment variable is set during a sweep. The first run of any
        config without decision data will fall back to summary-only display;
        re-run the sweep with the flag to populate the audit trail.
      </div>
    </div>
  );
}
