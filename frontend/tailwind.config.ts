import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Institutional palette - PRD v8.3
        background: "#F4F1EE", // Varmvit
        surface:    "#FFFFFF", // Card background
        primary:    "#2F2F2F", // Kolmörk Grå (text)
        muted:      "#6B6B6B", // Sekundär text
        positive:   "#4F8A8B", // Petroleum (Buy / OK)
        negative:   "#B35A44", // Terracotta (Sell / Warning)
        // Semantic aliases requested in PRD v8.3 (raw hex names)
        bg:         "#F4F1EE",
        text:       "#2F2F2F",
        buy:        "#4F8A8B",
        warning:    "#B35A44",
        accent:     "#C9A24E", // Optional gold accent for premium signals
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
