#!/usr/bin/env node
/**
 * Ensures platform-specific native binaries are installed before the build.
 * Works around the npm optional-dependency skip bug on Linux CI/CD environments.
 * See: https://github.com/npm/cli/issues/4828
 */
"use strict";
const { execSync } = require("child_process");
const { platform, arch } = require("process");

if (platform !== "linux" || arch !== "x64") {
  console.log("[native] Not linux-x64, skipping native binary check.");
  process.exit(0);
}

const BINARIES = [
  "@esbuild/linux-x64@0.25.12",
  "@napi-rs/lzma-linux-x64-gnu@1.5.1",
  "@rollup/rollup-linux-x64-gnu@4.63.3",
  "@rollup/rollup-linux-x64-musl@4.63.3",
  "lightningcss-linux-x64-gnu@1.32.0",
  "lightningcss-linux-x64-musl@1.32.0",
];

const missing = BINARIES.filter((pkg) => {
  const name = pkg.replace(/@[^@]+$/, "");
  try {
    require.resolve(name);
    return false;
  } catch {
    return true;
  }
});

if (missing.length === 0) {
  console.log("[native] All linux-x64 binaries present. ?");
  process.exit(0);
}

console.log("[native] Installing missing linux-x64 binaries:", missing);
execSync(`npm install --no-save --prefer-offline ${missing.join(" ")}`, {
  stdio: "inherit",
  cwd: process.cwd(),
});
console.log("[native] Done. ?");
