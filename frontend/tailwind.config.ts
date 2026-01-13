import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // 赛博朋克高科技配色
        'deep-space': '#0a0a0f',
        'dark-purple': '#1a1a2e',
        'cyber-blue': '#00d4ff',
        'neon-purple': '#a855f7',
        'cyber-green': '#00ff88',
        'energy-orange': '#ff6b35',
        'alert-red': '#ff3366',
      },
      fontFamily: {
        'tech': ['Orbitron', 'Rajdhani', 'sans-serif'],
        'mono': ['JetBrains Mono', 'Space Mono', 'monospace'],
        'chinese': ['Noto Sans SC', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'cyber-gradient': 'linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%)',
        'glow-gradient': 'linear-gradient(90deg, transparent, #00d4ff, transparent)',
      },
      animation: {
        'glow': 'glow 2s ease-in-out infinite alternate',
        'float': 'float 3s ease-in-out infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px #00d4ff, 0 0 10px #00d4ff' },
          '100%': { boxShadow: '0 0 10px #00d4ff, 0 0 20px #00d4ff, 0 0 30px #00d4ff' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      boxShadow: {
        'cyber': '0 0 15px rgba(0, 212, 255, 0.3)',
        'cyber-lg': '0 0 30px rgba(0, 212, 255, 0.4)',
        'neon': '0 0 15px rgba(168, 85, 247, 0.3)',
      },
    },
  },
  plugins: [],
}

export default config
