import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: { DEFAULT: "#0e1117", surface: "#161b22", elevated: "#1f2937" },
        border: { DEFAULT: "#30363d", subtle: "#21262d" },
        ink: { DEFAULT: "#e5e7eb", muted: "#9ca3af", subtle: "#6b7280" },
        // Policy-coded palette (matches thesis figures)
        policy: {
          mas: "#2A9D8F",
          periodic: "#E69F00",
          rop: "#D55E00",
        },
        accent: { DEFAULT: "#2A9D8F", muted: "#1e7d6f" },
      },
      fontFamily: {
        sans: [
          "ui-sans-serif", "system-ui", "-apple-system", "BlinkMacSystemFont",
          "Segoe UI", "Roboto", "sans-serif",
        ],
        mono: [
          "ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
