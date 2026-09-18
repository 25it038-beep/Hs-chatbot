#!/usr/bin/env node
/**
 * Ensures platform-specific native binaries are installed before the build.
 * Works around the npm optional-dependency skip bug on Linux CI/CD environments.
 * See: https://github.com/npm/cli/issues/4828
 *
 * Always installs into the REPO ROOT node_modules (one level up from this
 * script's location) so that lightningcss / esbuild / rollup can resolve them,
 * regardless of which working directory Render or any other CI uses.
 */
"use strict";
const { execSync } = require("child_process");
const path = require("path");
const { platform, arch } = require("process");

if (platform !== "linux" || arch !== "x64") {
  console.log("[native] Not linux-x64, skipping native binary check.");
  process.exit(0);
}

// __dirname = <repo-root>/scripts  =>  repoRoot = <repo-root>
const repoRoot = path.resolve(__dirname, "..");

const BINARIES = [
  "@esbuild/linux-x64@0.25.12",
  "@napi-rs/lzma-linux-x64-gnu@1.5.1",
  "@rollup/rollup-linux-x64-gnu@4.63.3",
  "@rollup/rollup-linux-x64-musl@4.63.3",
  "lightningcss-linux-x64-gnu@1.32.0",
  "lightningcss-linux-x64-musl@1.32.0",
];

// Check from repoRoot so Node resolves against root node_modules
const missing = BINARIES.filter((pkg) => {
  const name = pkg.replace(/@[^@]+$/, "");
  try {
    require.resolve(name, { paths: [repoRoot] });
    return false;
  } catch {
    return true;
  }
});

if (missing.length === 0) {
  console.log("[native] All linux-x64 binaries present. OK");
  process.exit(0);
}

console.log("[native] Installing missing linux-x64 binaries:", missing.join(", "));
// Install at repo root so binaries land in root node_modules (not workspace-local)
execSync(`npm install --no-save ${missing.join(" ")}`, {
  stdio: "inherit",
  cwd: repoRoot,
});
console.log("[native] Done.");
