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
        canvas: {
          DEFAULT: "#F6F5F2",
          muted: "#EFECE6",
          surface: "#FFFFFF",
          border: "#D6D3CD",
        },
        ink: {
          DEFAULT: "#18181B",
          secondary: "#3F3F46",
          muted: "#71717A",
        },
        ops: {
          navy: "#1E3A8A",
          navyBg: "#DBEAFE",
          green: "#166534",
          greenBg: "#DCFCE7",
          amber: "#9A3412",
          amberBg: "#FFEDD5",
          red: "#991B1B",
          redBg: "#FEE2E2",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
