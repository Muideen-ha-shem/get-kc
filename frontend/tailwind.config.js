/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#14171D',
          soft: '#20242E',
        },
        paper: '#ECEEF2',
        gold: {
          50: '#FBF5E7',
          100: '#F3E4C0',
          200: '#E8CD8E',
          300: '#DCB662',
          400: '#CBA045',
          500: '#C89A3E',
          600: '#A9821F',
          700: '#8A6A19',
        },
      },
      fontFamily: {
        display: ['Georgia', '"Iowan Old Style"', '"Palatino Linotype"', '"Book Antiqua"', 'serif'],
      },
    },
  },
  plugins: [],
};
