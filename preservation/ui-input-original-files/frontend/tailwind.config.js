/** @type {import('tailwindcss').Config} */
// Dark navy + purple-blue theme. Existing pages use these token names (bg-white, border-mist, text-ink, ...), so
// re-pointing the tokens re-themes the whole app. `bg-white` becomes the panel surface; `text-white` stays white.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        fog: "#060B1E",                                                   // page background
        ink: { DEFAULT: "#EAEFFF", soft: "#B6C0E4", faint: "#8794C0" },   // text
        mist: "#2A3766",                                                  // borders
        route: { DEFAULT: "#8FB0FF", dark: "#B3C8FF", tint: "#1E2A5E" }, // links / selected
        signal: "#FBBF24",
        moss: "#34D399",
        alert: "#FB7185",
        glow: { blue: "#3B82FF", violet: "#8B5CFF", cyan: "#35E0D2" },
      },
      backgroundColor: {
        white: "#0E1636",                         // panel surface
        "green-50": "rgba(52,211,153,.14)",
        "green-100": "rgba(52,211,153,.18)",
        "red-50": "rgba(251,113,133,.14)",
        "red-100": "rgba(251,113,133,.18)",
      },
      backgroundImage: { brand: "linear-gradient(135deg,#3B82FF 0%,#7C5CFF 58%,#B35CFF 100%)" },
      boxShadow: { glow: "0 0 22px rgba(124,92,255,.38)", "glow-cyan": "0 0 18px rgba(53,224,210,.35)" },
      fontFamily: {
        display: ['"Bricolage Grotesque"', "system-ui", "sans-serif"],
        sans: ['"Instrument Sans"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
