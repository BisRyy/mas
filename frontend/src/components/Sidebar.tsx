"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity, BarChart3, Beaker, FlaskConical, Github, GitCompare,
  Info, LayoutDashboard, PlayCircle, Search, ScrollText, Settings,
} from "lucide-react";

const GITHUB_URL = "https://github.com/BisRyy/mas";

const NAV = [
  { href: "/", label: "Overview", Icon: LayoutDashboard },
  { href: "/about", label: "About", Icon: Info },
  { href: "/experiments", label: "Experiments", Icon: FlaskConical },
  { href: "/compare", label: "Comparison", Icon: GitCompare },
  { href: "/decisions", label: "Decision audit", Icon: Search },
  { href: "/reports/h1", label: "H1 — Performance", Icon: BarChart3 },
  { href: "/reports/h3", label: "H3 — Scalability", Icon: Activity },
  { href: "/reports/ablation", label: "Ablation", Icon: Beaker },
  { href: "/runs", label: "Runs", Icon: ScrollText },
  { href: "/runs/new", label: "Launch run", Icon: PlayCircle },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden md:flex md:w-60 md:flex-col md:border-r md:border-border md:bg-bg-surface">
      <div className="border-b border-border px-5 py-5">
        <div className="text-xs uppercase tracking-wider text-ink-muted">
          Inventory MAS
        </div>
        <div className="mt-0.5 text-base font-semibold text-ink">Thesis console</div>
      </div>
      <nav className="flex-1 space-y-0.5 px-2 py-3 text-sm">
        {NAV.map(({ href, label, Icon }) => {
          const active =
            pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={[
                "flex items-center gap-2 rounded-md px-3 py-2",
                "text-ink-muted hover:bg-bg-elevated hover:text-ink",
                active && "bg-bg-elevated font-medium text-ink",
              ].filter(Boolean).join(" ")}
            >
              <Icon size={16} strokeWidth={1.75} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="space-y-2 border-t border-border px-5 py-3">
        <Link
          href="/settings"
          className="flex items-center gap-2 text-xs text-ink-subtle hover:text-ink"
        >
          <Settings size={14} />
          Settings
        </Link>
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-xs text-ink-subtle hover:text-ink"
        >
          <Github size={14} />
          GitHub
        </a>
      </div>
    </aside>
  );
}
