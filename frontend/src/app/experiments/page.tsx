"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";
import { api, type ExperimentSummary } from "@/lib/api";
import { pct, money, num, policyLabel } from "@/lib/format";

const FAMILY_OPTIONS = ["all", "h1", "h3", "ablation", "custom"];
const POLICY_OPTIONS = ["all", "mas", "periodic_forecasting", "static_rop",
                        "full", "no_adwin", "ma_only", "no_safety"];

export default function ExperimentsPage() {
  const [family, setFamily] = useState("all");
  const [policy, setPolicy] = useState("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<keyof ExperimentSummary>("config_name");
  const [desc, setDesc] = useState(false);

  const q = useQuery({
    queryKey: ["experiments", { family, policy }],
    queryFn: () =>
      api.listExperiments({
        family: family === "all" ? undefined : family,
        policy: policy === "all" ? undefined : policy,
        limit: 500,
      }),
  });

  const rows = useMemo(() => {
    let data = q.data ?? [];
    if (search) {
      data = data.filter((e) =>
        e.config_name.toLowerCase().includes(search.toLowerCase()),
      );
    }
    data = [...data].sort((a, b) => {
      const av = a[sort];
      const bv = b[sort];
      if (av === null) return 1;
      if (bv === null) return -1;
      if (typeof av === "number" && typeof bv === "number")
        return desc ? bv - av : av - bv;
      return desc
        ? String(bv).localeCompare(String(av))
        : String(av).localeCompare(String(bv));
    });
    return data;
  }, [q.data, search, sort, desc]);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">Experiment catalog</h1>
        <p className="text-ink-muted">
          {rows.length} experiments shown.
          {q.data && q.data.length !== rows.length &&
            ` (${q.data.length} total before filter)`}
        </p>
      </header>

      <div className="card flex flex-wrap items-end gap-3">
        <Select label="Family" value={family} onChange={setFamily} options={FAMILY_OPTIONS} />
        <Select label="Policy" value={policy} onChange={setPolicy} options={POLICY_OPTIONS} />
        <div className="flex flex-col">
          <label className="metric-label">Search</label>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="config name…"
            className="mt-1 w-56 rounded-md border border-border bg-bg-elevated px-3 py-1.5 text-sm text-ink"
          />
        </div>
      </div>

      <div className="card overflow-hidden p-0">
        <table>
          <thead>
            <tr>
              <Th col="config_name" sort={sort} setSort={setSort} desc={desc} setDesc={setDesc}>
                Config
              </Th>
              <Th col="family" sort={sort} setSort={setSort} desc={desc} setDesc={setDesc}>
                Family
              </Th>
              <Th col="policy" sort={sort} setSort={setSort} desc={desc} setDesc={setDesc}>
                Policy
              </Th>
              <Th col="scenario" sort={sort} setSort={setSort} desc={desc} setDesc={setDesc}>
                Scenario
              </Th>
              <Th col="n_seeds" sort={sort} setSort={setSort} desc={desc} setDesc={setDesc}>
                Seeds
              </Th>
              <Th col="mean_stockout_rate" sort={sort} setSort={setSort} desc={desc} setDesc={setDesc} align="right">
                Stockout
              </Th>
              <Th col="mean_total_cost" sort={sort} setSort={setSort} desc={desc} setDesc={setDesc} align="right">
                Cost
              </Th>
              <Th col="mean_n_orders" sort={sort} setSort={setSort} desc={desc} setDesc={setDesc} align="right">
                Orders
              </Th>
              <Th col="mean_forecast_mape" sort={sort} setSort={setSort} desc={desc} setDesc={setDesc} align="right">
                MAPE
              </Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((e) => (
              <tr key={e.id}>
                <td>
                  <Link href={`/experiments/${e.config_name}`} className="font-mono">
                    {e.config_name}
                  </Link>
                </td>
                <td className="uppercase text-xs text-ink-muted">{e.family}</td>
                <td>
                  <span className={`policy-dot ${e.policy}`} />
                  {policyLabel(e.policy)}
                </td>
                <td className="text-xs text-ink-muted">{e.scenario}</td>
                <td>{e.n_seeds}</td>
                <td className="text-right">{pct(e.mean_stockout_rate)}</td>
                <td className="text-right">{money(e.mean_total_cost)}</td>
                <td className="text-right">{num(e.mean_n_orders)}</td>
                <td className="text-right">{pct(e.mean_forecast_mape)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Select({
  label, value, onChange, options,
}: { label: string; value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <div className="flex flex-col">
      <label className="metric-label">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 rounded-md border border-border bg-bg-elevated px-3 py-1.5 text-sm text-ink"
      >
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </div>
  );
}

function Th({
  col, sort, setSort, desc, setDesc, align = "left", children,
}: {
  col: string;
  sort: string;
  setSort: (v: never) => void;
  desc: boolean;
  setDesc: (v: boolean) => void;
  align?: "left" | "right";
  children: React.ReactNode;
}) {
  const active = sort === col;
  return (
    <th
      className={`cursor-pointer select-none ${align === "right" ? "text-right" : ""}`}
      onClick={() => {
        if (active) setDesc(!desc);
        else {
          setSort(col as never);
          setDesc(false);
        }
      }}
    >
      <span>
        {children} {active ? (desc ? "↓" : "↑") : ""}
      </span>
    </th>
  );
}
