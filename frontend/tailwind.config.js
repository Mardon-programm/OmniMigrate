/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0b0e14",
        surface: "#11151e",
        surface2: "#171c27",
        border: "#232a38",
        primary: "#6366f1",
        "primary-600": "#4f46e5",
        "primary-400": "#818cf8",
        accent: "#22d3ee",
        success: "#34d399",
        warning: "#fbbf24",
        danger: "#f87171",
        muted: "#8b93a7",
        code: "#0d1117",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(99,102,241,0.25), 0 8px 40px -12px rgba(99,102,241,0.45)",
        "glow-sm": "0 4px 20px -8px rgba(99,102,241,0.4)",
        "glow-cyan": "0 0 0 1px rgba(34,211,238,0.2), 0 8px 40px -12px rgba(34,211,238,0.35)",
        card: "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 12px 40px -20px rgba(0,0,0,0.6)",
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, #6366f1 0%, #22d3ee 100%)",
        "brand-gradient-soft":
          "linear-gradient(135deg, rgba(99,102,241,0.16) 0%, rgba(34,211,238,0.16) 100%)",
      },
      animation: {
        "fade-in": "fadeIn 0.25s ease-out",
        "scale-in": "scaleIn 0.18s ease-out",
        float: "float 8s ease-in-out infinite",
        "float-delayed": "float 10s ease-in-out 2s infinite",
        shimmer: "shimmer 2.4s linear infinite",
        "gradient-x": "gradientX 8s ease infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        scaleIn: {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        float: {
          "0%, 100%": { transform: "translate(0, 0) scale(1)" },
          "50%": { transform: "translate(24px, -20px) scale(1.08)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        gradientX: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
      },
    },
  },
  plugins: [],
};
