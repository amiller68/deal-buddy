/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./src/**/*.py",
  ],
  theme: {
    extend: {
      colors: {
        'beige': '#f0e7d5',
        'dark-beige': '#d4ccba',
        'orange': '#ff6600',
        'dark-orange': '#d64b07',
        'black': '#000000',
      },
      fontFamily: {
        'roboto': ['"Roboto"', 'monospace'],
      },
      boxShadow: {
        'header': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
      },
      borderWidth: {
        '2': '2px',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        }
      },
      animation: {
        'fade-in': 'fade-in 0.5s ease-out'
      }
    },
  },
  plugins: [],
}