import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}", "tests/**/*.test.{ts,tsx}"],
    // The first test in a jsdom worker pays the React/Testing Library import cost, which exceeds
    // the 5 s default on slow machines and shared CI runners.
    testTimeout: 20_000,
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      include: ["src/**"],
    },
  },
});
