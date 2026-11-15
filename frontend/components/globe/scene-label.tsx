"use client";

import { Html } from "@react-three/drei";

import { LABEL_OFFSET_PX } from "./constants";
import type { Vec3 } from "./geo";

/** Overlay z-indexes: under the component's own legend and lists. */
const LABEL_Z_RANGE = [20, 10];

interface SceneLabelProps {
  position: Vec3;
  text: string;
}

/** A small text tag floating above a point of the globe. Decorative: the text is also in the DOM lists. */
export function SceneLabel({ position, text }: SceneLabelProps) {
  return (
    <Html position={position} center zIndexRange={LABEL_Z_RANGE} pointerEvents="none">
      <div
        aria-hidden="true"
        style={{ transform: `translateY(-${LABEL_OFFSET_PX}px)` }}
        className="pointer-events-none -translate-y-1/2 rounded-sm border border-line-strong bg-deep/90 px-2 py-0.5 text-xs font-bold whitespace-nowrap text-white shadow-sm"
      >
        {text}
      </div>
    </Html>
  );
}
