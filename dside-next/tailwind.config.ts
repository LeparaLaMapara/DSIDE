import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#e6f5ee',
          100: '#b3e0cc',
          200: '#80ccaa',
          300: '#4db888',
          400: '#26a96b',
          500: '#007A4D',
          600: '#006e45',
          700: '#005f3b',
          800: '#005032',
          900: '#003a24',
          DEFAULT: '#007A4D',
        },
        secondary: {
          50: '#fff8e6',
          100: '#ffeab3',
          200: '#ffdd80',
          300: '#ffcf4d',
          400: '#ffc526',
          500: '#FFB612',
          600: '#e6a410',
          700: '#cc920e',
          800: '#b3800c',
          900: '#806009',
          DEFAULT: '#FFB612',
        },
        accent: {
          50: '#e6e8f2',
          100: '#b3b9d9',
          200: '#808abf',
          300: '#4d5ba6',
          400: '#263d93',
          500: '#002395',
          600: '#001f86',
          700: '#001a73',
          800: '#001660',
          900: '#001040',
          DEFAULT: '#002395',
        },
        danger: {
          50: '#fce8e7',
          100: '#f6b9b7',
          200: '#f08a87',
          300: '#ea5b57',
          400: '#e63e39',
          500: '#DE3831',
          600: '#c8322c',
          700: '#af2c27',
          800: '#962621',
          900: '#6b1b18',
          DEFAULT: '#DE3831',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
