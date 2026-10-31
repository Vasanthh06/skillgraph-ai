/** @type {import('tailwindcss').Config} */
// Dark navy + purple-blue theme. Existing pages use these token names (bg-white, border-mist, text-ink, ...), so
// re-pointing the tokens re-themes the whole app. `bg-white` becomes the panel surface; `text-white` stays white.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        fog: "rgb(var(--page) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        elevated: "rgb(var(--elevated) / <alpha-value>)",
        inset: "rgb(var(--inset) / <alpha-value>)",
        ink: { DEFAULT: "rgb(var(--text) / <alpha-value>)", soft: "rgb(var(--soft) / <alpha-value>)", faint: "rgb(var(--muted) / <alpha-value>)" },
        mist: "rgb(var(--border) / <alpha-value>)",
        route: { DEFAULT: "rgb(var(--accent) / <alpha-value>)", dark: "rgb(var(--accent-strong) / <alpha-value>)", tint: "rgb(var(--tint) / <alpha-value>)" },
        signal: "rgb(var(--warning) / <alpha-value>)", moss: "rgb(var(--success) / <alpha-value>)", alert: "rgb(var(--danger) / <alpha-value>)",
        glow: { blue: "rgb(var(--blue) / <alpha-value>)", violet: "rgb(var(--violet) / <alpha-value>)", cyan: "rgb(var(--teal) / <alpha-value>)" },
      },
      backgroundColor: {
        white: "rgb(var(--surface) / <alpha-value>)",
        "green-50": "rgb(var(--success) / 0.09)", "green-100": "rgb(var(--success) / 0.15)",
        "red-50": "rgb(var(--danger) / 0.09)", "red-100": "rgb(var(--danger) / 0.15)",
      },
      backgroundImage: { brand: "linear-gradient(135deg,#3B82FF 0%,#7C5CFF 58%,#B35CFF 100%)" },
      boxShadow: { glow: "var(--shadow-accent)", "glow-cyan": "var(--shadow-accent)" },
      fontFamily: {
        display: ['"Bricolage Grotesque"', "system-ui", "sans-serif"],
        sans: ['"Instrument Sans"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
