/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#090A0F",
        surface: "#131722",
        surface2: "#1E2433",
        border: "#1E293B",
        primary: "#10B981",
        "primary-600": "#059669",
        "primary-400": "#34D399",
        accent: "#06B6D4",
        success: "#10B981",
        warning: "#F59E0B",
        danger: "#EF4444",
        muted: "#94A3B8",
        code: "#000000",
        healing: "#A78BFA",
      },
      fontFamily: {
        sans: ["Inter", "Plus Jakarta Sans", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(16,185,129,0.25), 0 8px 40px -12px rgba(16,185,129,0.45)",
        "glow-sm": "0 4px 20px -8px rgba(16,185,129,0.4)",
        "glow-cyan": "0 0 0 1px rgba(6,182,212,0.2), 0 8px 40px -12px rgba(6,182,212,0.35)",
        card: "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 12px 40px -20px rgba(0,0,0,0.7)",
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, #10B981 0%, #06B6D4 100%)",
        "brand-gradient-soft":
          "linear-gradient(135deg, rgba(16,185,129,0.14) 0%, rgba(6,182,212,0.14) 100%)",
      },
      transitionTimingFunction: {
        spring: "cubic-bezier(0.34, 1.56, 0.64, 1)",
        smooth: "cubic-bezier(0.4, 0, 0.2, 1)",
      },
      animation: {
        "fade-in": "fadeIn 0.15s ease-out",
        "scale-in": "scaleIn 0.15s ease-out",
        float: "float 8s ease-in-out infinite",
        "float-delayed": "float 10s ease-in-out 2s infinite",
        shimmer: "shimmer 1.6s linear infinite",
        "gradient-x": "gradientX 6s ease infinite",
        blink: "blink 1.1s step-end infinite",
        aurora: "aurora 18s ease-in-out infinite alternate",
        "aurora-slow": "aurora 26s ease-in-out -8s infinite alternate-reverse",
        scan: "scan 7s linear infinite",
        "led-ping": "ledPing 2.2s cubic-bezier(0, 0, 0.2, 1) infinite",
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
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(250%)" },
        },
        gradientX: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
        aurora: {
          "0%": { transform: "translate(-8%, -4%) rotate(-4deg) scale(1)" },
          "50%": { transform: "translate(6%, 5%) rotate(3deg) scale(1.15)" },
          "100%": { transform: "translate(-4%, 8%) rotate(-2deg) scale(0.95)" },
        },
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(400%)" },
        },
        ledPing: {
          "0%": { transform: "scale(1)", opacity: "0.9" },
          "75%, 100%": { transform: "scale(2.6)", opacity: "0" },
        },
      },
    },
  },
  plugins: [],
};
