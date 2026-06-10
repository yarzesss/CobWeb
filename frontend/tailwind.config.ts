import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        cobweb: {
          bg: '#0d0d18',
          surface: '#1a1a2e',
          surface2: '#252542',
          border: '#3d3d5c',
          pink: '#C2185B',
          'pink-light': '#E91E8C',
          'pink-dark': '#880E4F',
          mint: '#4ade80',
          amber: '#fbbf24',
          red: '#ef4444',
          cyan: '#22d3ee',
        },
      },
      fontFamily: {
        pixel: ['var(--font-pixel)', 'monospace'],
        mono: ['var(--font-mono)', 'monospace'],
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        pixel: '4px 4px 0px 0px rgba(194, 24, 91, 0.6)',
        'pixel-sm': '2px 2px 0px 0px rgba(194, 24, 91, 0.5)',
        'pixel-inset': 'inset 2px 2px 0px 0px rgba(0,0,0,0.4)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        scanline: 'scanline 8s linear infinite',
      },
      keyframes: {
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
