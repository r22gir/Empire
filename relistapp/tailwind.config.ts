import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        gold: { DEFAULT: "#b8960c", light: "#fdf8eb", border: "#f0e6c0" },
        teal: { DEFAULT: "#06b6d4", light: "#ecfeff", dark: "#0891b2" },
      },
    },
  },
  plugins: [],
};
export default config;
