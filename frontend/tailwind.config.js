/** Design tokens. Colours are named for what they ARE in an academic setting (ink, paper, highlighter). */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#17233b", soft: "#2c3a56", muted: "#586175" },
        paper: { DEFAULT: "#f5f6f8", raised: "#ffffff" },
        rule: "#d8dce4",
        brand: { DEFAULT: "#1f6f5c", dark: "#17574a", tint: "#e2f0eb" },
        mark: { DEFAULT: "#f2c14e", tint: "#fcf1d2" },
        alert: { DEFAULT: "#b3261e", tint: "#fbe9e7" },
      },
      fontFamily: {
        serif: ['"Source Serif 4 Variable"', "Georgia", "serif"],
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
