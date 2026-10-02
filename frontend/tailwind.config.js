/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: 'var(--color-ink)',
          muted: 'var(--color-ink-muted)',
        },
        canvas: {
          DEFAULT: 'var(--color-canvas)',
        },
        surface: {
          DEFAULT: 'var(--color-surface)',
          muted: 'var(--color-surface-muted)',
        },
        border: {
          DEFAULT: 'var(--color-border)',
        },
        focus: {
          DEFAULT: 'var(--color-focus)',
          hover: 'var(--color-focus-hover)',
        },
        spark: {
          DEFAULT: 'var(--color-spark)',
        },
        weak: {
          DEFAULT: 'var(--color-weak)',
        },
        good: {
          DEFAULT: 'var(--color-good)',
        },
      },
      fontFamily: {
        heading: ['"Bricolage Grotesque"', 'sans-serif'],
        sans: ['Figtree', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        '2xl': '16px',
        'xl': '12px',
        'lg': '8px',
      },
      maxWidth: {
        'reading': '720px',
      },
    },
  },
  plugins: [],
}
