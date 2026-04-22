import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/components/QueryProvider";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Inventory MAS — Thesis Console",
  description:
    "Tracking, analytics, and reporting for the multi-agent inventory-optimization thesis.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>
        <QueryProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 overflow-x-auto">
              <div className="mx-auto max-w-7xl px-6 py-8">{children}</div>
            </main>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
