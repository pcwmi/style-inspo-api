/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'bone': '#FAF7F2',
        'ink': '#1a1614',
        'muted': '#6B625A',
        'terracotta': '#C85A3E',
        'sand': '#E8DED2',
      },
      fontFamily: {
        'serif': ['Libre Baskerville', 'serif'],
        'sans': ['DM Sans', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

