/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          main: '#121211',
          card: '#181715',
          cardHover: '#1c1b18',
          subtle: '#22211e',
        },
        border: {
          subtle: '#2a2824',
          muted: '#36342e',
        },
        status: {
          operational: '#74b946',   // Olive-green from screenshot
          degraded: '#e28725',      // Amber from screenshot
          down: '#d6453d',          // Red from screenshot
          nodata: '#2d2c27',        // Dim gray
        }
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
      }
    },
  },
  plugins: [],
}
