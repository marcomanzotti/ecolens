"use client";

import { useSyncExternalStore } from "react";

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

function subscribeReducedMotion(onChange: () => void): () => void {
  const query = window.matchMedia(REDUCED_MOTION_QUERY);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

/** True when the user asked the system for less motion. False while rendering on the server. */
export function useReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribeReducedMotion,
    () => window.matchMedia(REDUCED_MOTION_QUERY).matches,
    () => false,
  );
}

let webglSupport: boolean | null = null;

/** Probes WebGL once, then releases the probe's context (browsers allow only a few at a time). */
function detectWebGL(): boolean {
  if (webglSupport === null) {
    try {
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("webgl2") ?? canvas.getContext("webgl");
      webglSupport = context !== null;
      context?.getExtension("WEBGL_lose_context")?.loseContext();
    } catch {
      webglSupport = false;
    }
  }
  return webglSupport;
}

function subscribeNever(): () => void {
  return () => {};
}

/** Whether WebGL works here: null on the server and until the client has checked. */
export function useWebGLSupport(): boolean | null {
  return useSyncExternalStore<boolean | null>(subscribeNever, detectWebGL, () => null);
}
