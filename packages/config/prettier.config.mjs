import { fileURLToPath } from "node:url";

/** @type {import("prettier").Config} */
const config = {
  printWidth: 100,
  singleQuote: false,
  semi: true,
  trailingComma: "all",
  // Resolved relative to this package so every workspace (and the repo root) can load it.
  plugins: [fileURLToPath(import.meta.resolve("prettier-plugin-tailwindcss"))],
  tailwindStylesheet: fileURLToPath(new URL("../../apps/web/src/app/globals.css", import.meta.url)),
};

export default config;
