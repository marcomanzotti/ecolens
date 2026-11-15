"use client";

import { useLayoutEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Color, DoubleSide, Object3D, type InstancedMesh, type ShaderMaterial } from "three";

import {
  RENDER_ORDER,
  TIMELAPSE_RING_MAX_CELLS,
  TIMELAPSE_RING_MS,
  TIMELAPSE_RING_OPACITY,
  TIMELAPSE_RING_RADIUS,
} from "./constants";
import { degToRad, latLonToVec3 } from "./geo";
import { noRaycast } from "./markers";
import type { TimelapseData } from "./timelapse-data";
import { newlyEmerged } from "./timelapse-front";
import { RING_FRAGMENT, RING_VERTEX } from "./timelapse-shader";

const RING_INNER = 0.9;
const RING_SEGMENTS = 32;
/** Ring size when it is emitted, in cells. */
const RING_START_CELLS = 0.5;

interface TimelapseRingsProps {
  data: TimelapseData;
  frame: Int8Array;
  previous: Int8Array;
}

/**
 * One expanding ring per cell whose trend became significant this very year (it was not the
 * year before). Mounted once per year (keyed by the year), it plays once and then hides.
 */
export function TimelapseRings({ data, frame, previous }: TimelapseRingsProps) {
  const events = useMemo(() => newlyEmerged(frame, previous), [frame, previous]);
  const { n_lon, lat_first, lon_first, step_deg } = data.meta.grid;
  const meshRef = useRef<InstancedMesh>(null);
  const start = useRef<number | null>(null);
  const uniforms = useMemo(
    () => ({
      progress: { value: 0 },
      startScale: { value: RING_START_CELLS },
      endScale: { value: TIMELAPSE_RING_MAX_CELLS },
      ringOpacity: { value: TIMELAPSE_RING_OPACITY },
    }),
    [],
  );

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    const dummy = new Object3D();
    const warming = new Color(data.dataset.frontColors.up);
    const cooling = new Color(data.dataset.frontColors.down);
    const cellSize = degToRad(step_deg);
    events.forEach(({ cell, direction }, i) => {
      const lat = lat_first + Math.floor(cell / n_lon) * step_deg;
      const lon = lon_first + (cell % n_lon) * step_deg;
      const [x, y, z] = latLonToVec3(lat, lon, TIMELAPSE_RING_RADIUS);
      dummy.position.set(x, y, z);
      dummy.lookAt(x * 2, y * 2, z * 2);
      dummy.scale.setScalar(cellSize);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
      mesh.setColorAt(i, direction > 0 ? warming : cooling);
    });
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, [events, n_lon, lat_first, lon_first, step_deg, data.dataset]);

  useFrame(() => {
    const mesh = meshRef.current;
    if (!mesh || !mesh.visible) return;
    const now = performance.now();
    start.current ??= now;
    const progress = Math.min(1, (now - start.current) / TIMELAPSE_RING_MS);
    (mesh.material as ShaderMaterial).uniforms.progress.value = progress;
    if (progress >= 1) mesh.visible = false;
  });

  if (events.length === 0) return null;
  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, events.length]}
      raycast={noRaycast}
      renderOrder={RENDER_ORDER.ring}
      frustumCulled={false}
    >
      <ringGeometry args={[RING_INNER, 1, RING_SEGMENTS]} />
      <shaderMaterial
        vertexShader={RING_VERTEX}
        fragmentShader={RING_FRAGMENT}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        side={DoubleSide}
      />
    </instancedMesh>
  );
}
