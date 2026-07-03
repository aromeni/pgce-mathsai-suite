/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0d0d14",
        surface: "#13131e",
        border: "rgba(255,255,255,0.07)",
        accent: "#00d4b8",
        "text-primary": "#e8e8f0",
        "text-secondary": "#7070a0",
        tier: {
          foundation: "#4ade80",
          developing: "#facc15",
          extending: "#f87171",
        },
      },
      fontFamily: {
        mono: ["DM Mono", "monospace"],
        display: ["Syne", "sans-serif"],
      },
    },
  },
  plugins: [],
};
