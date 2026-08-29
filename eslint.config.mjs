export default [
  {
    ignores: [
      "**/node_modules/**",
      "**/.next/**",
      "**/dist/**",
      "**/coverage/**",
      "**/.turbo/**",
      "**/.venv/**",
    ],
  },
  {
    files: ["**/*.{js,mjs,cjs}"],
    rules: {},
  },
];
