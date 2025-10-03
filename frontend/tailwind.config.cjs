/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#0b0f14',      // page background
        surface: '#0f141a',      // cards
        border:  '#2b2f36',      // subtle borders
        accent:  '#f59e0b',      // Censys-ish orange
        accent2: '#fbbf24',      // hover
      },
      boxShadow: {
        soft: '0 10px 25px rgba(0,0,0,0.25)'
      },
      fontFamily: {
        ui: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif']
      }
    },
  },
  plugins: [],
};
