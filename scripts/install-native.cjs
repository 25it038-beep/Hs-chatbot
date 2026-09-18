#!/usr/bin/env node
/**
 * Force-installs linux-x64 native binaries before the vite build.
 * Runs only on linux-x64 (Render / CI). No-ops on Windows/macOS.
 *
 * WHY --force:
 *   npm caches optional-dependency stubs (directory exists, package.json present)
 *   but skips downloading the actual .node binary when the lock was generated on
 *   a different platform. require.resolve() returns true for these stubs, so a
 *   simple presence-check gives false positives. --force bypasses the cache and
 *   ensures the real binary tarball is downloaded and extracted every time.
 *
 * WHY repoRoot cwd:
 *   Render sets root dir = frontend/, so this script runs from frontend/.
 *   npm install must run at the REPO ROOT so binaries land in root node_modules
 *   where lightningcss / esbuild / rollup actually resolve them from.
 */
"use strict";
const { execSync } = require("child_process");
const path = require("path");
const { platform, arch } = require("process");

if (platform !== "linux" || arch !== "x64") {
  console.log("[native] Not linux-x64 — skipping.");
  process.exit(0);
}

// __dirname = <repo>/scripts  =>  repoRoot = <repo>/
const repoRoot = path.resolve(__dirname, "..");

const BINARIES = [
  "@esbuild/linux-x64@0.25.12",
  "@napi-rs/lzma-linux-x64-gnu@1.5.1",
  "@rollup/rollup-linux-x64-gnu@4.63.3",
  "@rollup/rollup-linux-x64-musl@4.63.3",
  "lightningcss-linux-x64-gnu@1.32.0",
  "lightningcss-linux-x64-musl@1.32.0",
];

console.log("[native] Force-installing linux-x64 native binaries into", repoRoot);
execSync(
  "npm install --no-save --force " + BINARIES.join(" "),
  { stdio: "inherit", cwd: repoRoot }
);
console.log("[native] Done.");
