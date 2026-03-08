import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        gold: { DEFAULT: "#D4A030", light: "#F5E6C8", dark: "#B8860B", deep: "#8B6914" },
        sunrise: { DEFAULT: "#FF8C42", light: "#FFD4B0", dark: "#E67320" },
        earth: { DEFAULT: "#8B6F47", light: "#D4C4A8", dark: "#6B5230" },
        sage: { DEFAULT: "#7CB98B", light: "#E8F5EC", dark: "#5A9A6A" },
        lavender: { DEFAULT: "#9B8EC4", light: "#EDE8F5", dark: "#7B6EA4" },
        warmwhite: "#FFF9F0",
        cream: "#FEF7EC",
        sand: "#F5EDE0",
      },
      fontFamily: {
        serif: ["Playfair Display", "Georgia", "serif"],
        sans: ["Nunito", "system-ui", "sans-serif"],
      },
      animation: {
        "fade-up": "fadeUp 0.6s ease-out forwards",
        "float": "float 3s ease-in-out infinite",
        "flicker": "flicker 1.5s ease-in-out infinite",
        "shimmer": "shimmer 3s linear infinite",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
        flicker: {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.8", transform: "scale(1.1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "0% center" },
          "100%": { backgroundPosition: "200% center" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
