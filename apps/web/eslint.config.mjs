import js from "@eslint/js";
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";
import prettier from "eslint-config-prettier";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts", "coverage/**"],
  },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      // Business rules live on the server; the UI must not hide behaviour behind `any`.
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/consistent-type-imports": ["error", { prefer: "type-imports" }],
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "@typescript-eslint/restrict-template-expressions": ["error", { allowNumber: true }],
      // User-facing strings must come from next-intl messages (NFR-01).
      "react/jsx-no-literals": [
        "warn",
        { noStrings: true, ignoreProps: true, allowedStrings: ["404"] },
      ],
      // Accessibility (NFR-03): eslint-config-next registers jsx-a11y; tighten to strict-level.
      "jsx-a11y/alt-text": "error",
      "jsx-a11y/anchor-has-content": "error",
      "jsx-a11y/anchor-is-valid": "error",
      "jsx-a11y/aria-props": "error",
      "jsx-a11y/aria-proptypes": "error",
      "jsx-a11y/aria-role": "error",
      "jsx-a11y/click-events-have-key-events": "error",
      "jsx-a11y/control-has-associated-label": "error",
      "jsx-a11y/heading-has-content": "error",
      "jsx-a11y/html-has-lang": "error",
      "jsx-a11y/label-has-associated-control": "error",
      "jsx-a11y/no-autofocus": "error",
      "jsx-a11y/no-static-element-interactions": "error",
      "jsx-a11y/role-has-required-aria-props": "error",
      "jsx-a11y/role-supports-aria-props": "error",
    },
  },
  {
    files: ["**/*.test.{ts,tsx}", "tests/**"],
    rules: {
      "react/jsx-no-literals": "off",
      "@typescript-eslint/no-non-null-assertion": "off",
    },
  },
  {
    files: ["*.config.{ts,mjs}", "postcss.config.mjs", "vitest.setup.ts"],
    ...tseslint.configs.disableTypeChecked,
  },
  prettier,
);
