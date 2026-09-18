#!/usr/bin/env node
/**
 * Force-installs ALL linux-x64 native binaries into root node_modules
 * before vite build runs. Runs only on linux-x64 (Render/CI). No-ops elsewhere.
 *
 * WHY THIS EXISTS:
 *   npm has a known bug where optional platform-specific binaries are not
 *   installed when the lock file was generated on a different OS (e.g. Windows).
 *   These packages are declared in root package.json optionalDependencies AND
 *   here as a last-resort guardrail. See: https://github.com/npm/cli/issues/4828
 *
 * PACKAGES COVERED:
 *   @tailwindcss/oxide-linux-x64-gnu  <- Tailwind v4 Rust engine (THE ACTUAL ROOT CAUSE)
 *   @tailwindcss/oxide-linux-x64-musl <- same, for Alpine/musl Linux
 *   @esbuild/linux-x64                <- Vite config bundler
 *   @napi-rs/lzma-linux-x64-gnu      <- Rollup compression
 *   @rollup/rollup-linux-x64-gnu      <- Vite bundler (glibc)
 *   @rollup/rollup-linux-x64-musl     <- Vite bundler (musl)
 *   lightningcss-linux-x64-gnu        <- Tailwind CSS transform
 *   lightningcss-linux-x64-musl       <- Tailwind CSS transform (musl)
 *
 * INSTALL CWD: always repo root (one level up from /scripts/) so that
 * packages land in root node_modules where the parent packages resolve them.
 */
"use strict";
const { execSync } = require("child_process");
const path = require("path");
const { platform, arch } = require("process");

if (platform !== "linux" || arch !== "x64") {
  console.log("[native] Not linux-x64 -- skipping.");
  process.exit(0);
}

// __dirname = <repo>/scripts  =>  repoRoot = <repo>/
const repoRoot = path.resolve(__dirname, "..");

const BINARIES = [
  "@tailwindcss/oxide-linux-x64-gnu@4.3.3",
  "@tailwindcss/oxide-linux-x64-musl@4.3.3",
  "@esbuild/linux-x64@0.25.12",
  "@napi-rs/lzma-linux-x64-gnu@1.5.1",
  "@rollup/rollup-linux-x64-gnu@4.63.3",
  "@rollup/rollup-linux-x64-musl@4.63.3",
  "lightningcss-linux-x64-gnu@1.32.0",
  "lightningcss-linux-x64-musl@1.32.0",
];

console.log("[native] Force-installing linux-x64 native binaries into: " + repoRoot);
console.log("[native] Packages: " + BINARIES.join(", "));

execSync(
  "npm install --no-save --force " + BINARIES.join(" "),
  { stdio: "inherit", cwd: repoRoot }
);

console.log("[native] All linux-x64 native binaries installed successfully.");
