/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Warme, minimalistische Palette
        sand: {
          50: "#faf8f5",
          100: "#f3ede4",
          200: "#e7dccd",
        },
        clay: {
          400: "#c98a6a",
          500: "#b9734f",
          600: "#a15d3d",
        },
        ink: {
          700: "#3a3530",
          800: "#2a2620",
          900: "#1c1916",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 8px 30px rgba(28, 25, 22, 0.08)",
      },
    },
  },
  plugins: [],
};
