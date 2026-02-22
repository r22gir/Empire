/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        empire: {
          dark: '#0a0a0f',
          darker: '#050508',
        }
      }
    },
  },
  plugins: [],
}
