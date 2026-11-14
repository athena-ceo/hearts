// Copyright (c) 2026 Athena Decision Systems SAS.
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        ui: ["'Familjen Grotesk'", "'Helvetica Neue'", "Arial", "sans-serif"],
        rank: ["'Zilla Slab'", "Georgia", "serif"],
        code: ["'Spline Sans Mono'", "Menlo", "monospace"],
      },
      colors: {
        felt: { DEFAULT: "#22265c", raised: "#2d3273", dot: "#33387f" },
        paper: "#fffefb",
        panel: "#f2f2fb",
        ink: "#14142b",
        quiet: "#565a7d",
        "on-felt": { DEFAULT: "#ffffff", quiet: "#c5c8ee" },
        heart: "#c80f35",
        marker: "#ffd84d",
        rule: "#cfd0e6",
      },
    },
  },
  plugins: [],
};
