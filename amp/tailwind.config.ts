import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        gold: { DEFAULT: "#E0A526", light: "#FFE3B3", dark: "#B8860B", deep: "#8B6914" },
        sunrise: { DEFAULT: "#F28C6B", light: "#FAD4C0", dark: "#E67320" },
        sage: { DEFAULT: "#7E9F84", light: "#E4EDE6", dark: "#5A7A60" },
        cream: "#FFF9F1",
        surface: { DEFAULT: "#FFFFFF", dark: "#1E1B3A" },
        night: { DEFAULT: "#14122B", card: "#1E1B3A", border: "#2E2A54" },
        ink: { DEFAULT: "#2B2622", soft: "#6B625A", muted: "#8C837A" },
      },
      fontFamily: {
        serif: ["var(--font-fraunces)", "Playfair Display", "Georgia", "serif"],
        sans: ["var(--font-inter)", "Nunito", "system-ui", "sans-serif"],
      },
      animation: {
        "fade-up": "fadeUp 0.6s ease-out forwards",
        "float": "float 4s ease-in-out infinite",
        "pulse-slow": "pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "breathe": "breathe 6s cubic-bezier(0.22, 1, 0.36, 1) infinite",
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
        breathe: {
          "0%, 100%": { transform: "scale(1)" },
          "50%": { transform: "scale(1.08)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
