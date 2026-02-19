import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        gold: {
          DEFAULT: '#C9A84C',
          light: '#E8C97A',
          dark: '#A07830',
        },
        charcoal: {
          DEFAULT: '#2C2C2C',
          light: '#3D3D3D',
          dark: '#1A1A1A',
        },
      },
    },
  },
  plugins: [],
};

export default config;
