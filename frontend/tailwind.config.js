export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        risk: {
          verylow: "#22c55e",
          low: "#eab308",
          moderate: "#f97316",
          high: "#ef4444",
          critical: "#a855f7",
        },
      },
    },
  },
  plugins: [],
};
