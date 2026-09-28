/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Base semantic colors
        bg: {
          primary: "#020617",      // slate-950
          secondary: "#0f172a",    // slate-900
          tertiary: "#1e293b",     // slate-800
          card: "#1e293b",         // slate-800
          cardHover: "#334155",    // slate-700
        },
        border: {
          primary: "#334155",      // slate-700
          secondary: "#475569",    // slate-600
          focus: "#10b981",        // emerald-500
          error: "#ef4444",        // red-500
        },
        text: {
          primary: "#f1f5f9",      // slate-100
          secondary: "#94a3b8",    // slate-400
          tertiary: "#64748b",     // slate-500
          inverse: "#020617",      // slate-950
        },
        // Brand colors
        brand: {
          emerald: "#10b981",      // emerald-500
          emeraldLight: "#34d399", // emerald-400
          emeraldDark: "#059669",  // emerald-600
          emeraldBg: "#064e3b",    // emerald-900
          cyan: "#06b6d4",         // cyan-500
          cyanLight: "#22d3ee",    // cyan-400
          cyanDark: "#0891b2",     // cyan-600
          cyanBg: "#164e63",       // cyan-900
        },
        // Semantic status colors
        success: {
          DEFAULT: "#10b981",
          bg: "#064e3b",
          border: "#059669",
          text: "#34d399",
        },
        warning: {
          DEFAULT: "#f59e0b",
          bg: "#78350f",
          border: "#d97706",
          text: "#fbbf24",
        },
        danger: {
          DEFAULT: "#ef4444",
          bg: "#7f1d1d",
          border: "#dc2626",
          text: "#f87171",
        },
        info: {
          DEFAULT: "#06b6d4",
          bg: "#164e63",
          border: "#0891b2",
          text: "#22d3ee",
        },
        // Legacy support (for gradual migration)
        background: "#020617",
        surface: "#0f172a",
        surface2: "#1e293b",
        primary: "#10b981",
        "primary-600": "#059669",
        "primary-400": "#34d399",
        accent: "#06b6d4",
        muted: "#94a3b8",
        code: "#020617",
        healing: "#a78bfa",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
        display: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      fontSize: {
        // Refined type scale
        'display-xl': ['4.5rem', { lineHeight: '1.1', letterSpacing: '-0.02em', fontWeight: '700' }],
        'display-lg': ['3.75rem', { lineHeight: '1.1', letterSpacing: '-0.02em', fontWeight: '700' }],
        'display-md': ['3rem', { lineHeight: '1.2', letterSpacing: '-0.01em', fontWeight: '700' }],
        'display-sm': ['2.25rem', { lineHeight: '1.2', letterSpacing: '-0.01em', fontWeight: '600' }],
        'heading-xl': ['1.875rem', { lineHeight: '1.3', letterSpacing: '-0.01em', fontWeight: '600' }],
        'heading-lg': ['1.5rem', { lineHeight: '1.3', letterSpacing: '-0.01em', fontWeight: '600' }],
        'heading-md': ['1.25rem', { lineHeight: '1.4', fontWeight: '600' }],
        'heading-sm': ['1.125rem', { lineHeight: '1.4', fontWeight: '600' }],
        'body-lg': ['1.125rem', { lineHeight: '1.6', fontWeight: '400' }],
        'body': ['1rem', { lineHeight: '1.6', fontWeight: '400' }],
        'body-sm': ['0.875rem', { lineHeight: '1.5', fontWeight: '400' }],
        'caption': ['0.75rem', { lineHeight: '1.5', fontWeight: '400' }],
        'overline': ['0.625rem', { lineHeight: '1.5', letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: '500' }],
        'code-sm': ['0.75rem', { lineHeight: '1.6', fontFamily: 'JetBrains Mono, monospace' }],
        'code': ['0.8125rem', { lineHeight: '1.65', fontFamily: 'JetBrains Mono, monospace' }],
        'code-lg': ['0.875rem', { lineHeight: '1.7', fontFamily: 'JetBrains Mono, monospace' }],
      },
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
        '26': '6.5rem',
        '30': '7.5rem',
      },
      borderRadius: {
        'xs': '0.25rem',
        'sm': '0.375rem',
        'md': '0.5rem',
        'lg': '0.75rem',
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgb(0 0 0 / 0.3), 0 1px 2px -1px rgb(0 0 0 / 0.3)',
        'card-hover': '0 10px 40px -10px rgb(0 0 0 / 0.5), 0 2px 8px -2px rgb(0 0 0 / 0.3)',
        'elevated': '0 20px 60px -20px rgb(0 0 0 / 0.6), 0 8px 24px -8px rgb(0 0 0 / 0.4)',
        'overlay': '0 25px 80px -25px rgb(0 0 0 / 0.7)',
        'focus': '0 0 0 3px rgb(16 185 129 / 0.4)',
        'focus-danger': '0 0 0 3px rgb(239 68 68 / 0.4)',
        'inner-glow': 'inset 0 1px 0 0 rgb(255 255 255 / 0.05)',
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, #10b981 0%, #06b6d4 100%)',
        'brand-gradient-soft': 'linear-gradient(135deg, rgba(16,185,129,0.1) 0%, rgba(6,182,212,0.1) 100%)',
        'emerald-gradient': 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
        'cyan-gradient': 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)',
        'mesh-gradient': 'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(16,185,129,0.15), transparent), radial-gradient(ellipse 60% 40% at 80% 100%, rgba(6,182,212,0.1), transparent)',
        'noise': "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
        'smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'snappy': 'cubic-bezier(0.2, 0, 0, 1)',
      },
      transitionDuration: {
        'fast': '100ms',
        'normal': '200ms',
        'slow': '300ms',
        'slower': '500ms',
      },
      animation: {
        'fade-in': 'fadeIn 200ms ease-out',
        'fade-out': 'fadeOut 200ms ease-in',
        'slide-up': 'slideUp 300ms ease-out',
        'slide-down': 'slideDown 300ms ease-out',
        'slide-in-right': 'slideInRight 300ms ease-out',
        'scale-in': 'scaleIn 200ms ease-out',
        'scale-out': 'scaleOut 200ms ease-in',
        'shimmer': 'shimmer 2s linear infinite',
        'pulse-soft': 'pulseSoft 3s ease-in-out infinite',
        'spin-slow': 'spin 3s linear infinite',
        'accordion-down': 'accordionDown 200ms ease-out',
        'accordion-up': 'accordionUp 200ms ease-in',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        scaleOut: {
          '0%': { opacity: '1', transform: 'scale(1)' },
          '100%': { opacity: '0', transform: 'scale(0.95)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        accordionDown: {
          '0%': { height: '0', opacity: '0' },
          '100%': { height: 'var(--radix-accordion-content-height)', opacity: '1' },
        },
        accordionUp: {
          '0%': { height: 'var(--radix-accordion-content-height)', opacity: '1' },
          '100%': { height: '0', opacity: '0' },
        },
      },
      zIndex: {
        'dropdown': '100',
        'sticky': '200',
        'modal': '300',
        'popover': '400',
        'tooltip': '500',
        'toast': '600',
      },
    },
  },
  plugins: [],
};