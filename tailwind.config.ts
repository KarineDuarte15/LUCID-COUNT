import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'background': '#0A192F',
        'container': '#112240',
        'primary-text': '#CCD6F6',
        'secondary-text': '#8892b0',
        'accent': '#D4AF37',
      },
    },
  },
  plugins: [],
};
export default config;