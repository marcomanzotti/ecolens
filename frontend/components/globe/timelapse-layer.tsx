"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import { Color, type DataTexture, type ShaderMaterial } from "three";

import {
  EARTH_SEGMENTS,
  RENDER_ORDER,
  TIMELAPSE_AREA_FILL_OPACITY,
  TIMELAPSE_FADE_MS,
  TIMELAPSE_FIELD_OPACITY,
  TIMELAPSE_FRONT_RADIUS,
  TIMELAPSE_FRONT_WIDTH_PX,
  TIMELAPSE_GLOW_OPACITY,
  TIMELAPSE_NOT_SIGNIFICANT_DIM,
  TIMELAPSE_RADIUS,
} from "./constants";
import { latLonToVec3, type Vec3 } from "./geo";
import { noRaycast } from "./markers";
import type { TimelapseData } from "./timelapse-data";
import { yearIndex } from "./timelapse-data";
import { emergedFrame, frontMask, frontSegments, gridShape, type Direction } from "./timelapse-front";
import { MISSING_COLOR, MISSING_HATCH_COLOR } from "./timelapse-palette";
import { TimelapseRings } from "./timelapse-rings";
import { FIELD_FRAGMENT, FIELD_VERTEX } from "./timelapse-shader";
import { anomalyFrameTexture, frontMaskTexture, paletteTexture } from "./timelapse-textures";

export interface TimelapseLayers {
  anomaly: boolean;
  emergence: boolean;
}

interface TimelapseLayerProps {
  data: TimelapseData;
  year: number;
  layers: TimelapseLayers;
  reducedMotion: boolean;
}

/** One texture per year, built on first use and kept: switching back and forth costs nothing. */
function frameTextureFrom(cache: Map<number, DataTexture>, data: TimelapseData, frame: number): DataTexture {
  const hit = cache.get(frame);
  if (hit) return hit;
  const texture = anomalyFrameTexture(data, frame);
  cache.set(frame, texture);
  return texture;
}

function toPoints(latLon: number[]): Vec3[] {
  const points: Vec3[] = [];
  for (let i = 0; i < latLon.length; i += 2) {
    points.push(latLonToVec3(latLon[i], latLon[i + 1], TIMELAPSE_FRONT_RADIUS));
  }
  return points;
}

function FrontLine({ frame, data, direction }: { frame: Int8Array; data: TimelapseData; direction: Direction }) {
  const points = useMemo(() => toPoints(frontSegments(frame, gridShape(data.meta), direction)), [frame, data, direction]);
  if (points.length === 0) return null;
  return (
    <Line
      points={points}
      segments
      color={direction > 0 ? data.dataset.frontColors.up : data.dataset.frontColors.down}
      lineWidth={TIMELAPSE_FRONT_WIDTH_PX}
      transparent
      depthWrite={false}
      renderOrder={RENDER_ORDER.front}
      raycast={noRaycast}
    />
  );
}

/** Time-lapse of one dataset: anomaly field, emergence front with its one-cell glow, and the rings. */
export function TimelapseLayer({ data, year, layers, reducedMotion }: TimelapseLayerProps) {
  const materialRef = useRef<ShaderMaterial>(null);
  const cacheRef = useRef(new Map<number, DataTexture>());
  useEffect(() => {
    const cache = cacheRef.current;
    return () => {
      cache.forEach((texture) => texture.dispose());
      cache.clear();
    };
  }, [data]);
  const frame = yearIndex(data.meta, year);
  const emerged = useMemo(() => emergedFrame(data.emerged, data.meta, frame), [data, frame]);
  const previousEmerged = useMemo(
    () => (frame > 0 ? emergedFrame(data.emerged, data.meta, frame - 1) : null),
    [data, frame],
  );
  const mask = useMemo(() => {
    const { nLon, nLat } = gridShape(data.meta);
    return frontMaskTexture(frontMask(emerged, gridShape(data.meta)), nLon, nLat);
  }, [emerged, data]);
  useEffect(() => () => mask.dispose(), [mask]);

  const { scale, frontColors } = data.dataset;
  const uniforms = useMemo(
    () => ({
      frameA: { value: null as DataTexture | null },
      frameB: { value: null as DataTexture | null },
      front: { value: null as DataTexture | null },
      palette: { value: paletteTexture(scale.bands) },
      mixT: { value: 1 },
      bandCount: { value: scale.bands.length },
      minK: { value: scale.min },
      stepK: { value: scale.step },
      encodeRange: { value: scale.encodeRange },
      showAnomaly: { value: 1 },
      showEmergence: { value: 1 },
      fieldOpacity: { value: TIMELAPSE_FIELD_OPACITY },
      notSignificantDim: { value: TIMELAPSE_NOT_SIGNIFICANT_DIM },
      areaFillOpacity: { value: TIMELAPSE_AREA_FILL_OPACITY },
      glowOpacity: { value: TIMELAPSE_GLOW_OPACITY },
      missingColor: { value: new Color(MISSING_COLOR) },
      hatchColor: { value: new Color(MISSING_HATCH_COLOR) },
      warmingColor: { value: new Color(frontColors.up) },
      coolingColor: { value: new Color(frontColors.down) },
    }),
    [scale, frontColors],
  );
  useEffect(() => () => uniforms.palette.value.dispose(), [uniforms]);

  // Crossfade: from the frame on screen to the new year's frame, linear, TIMELAPSE_FADE_MS.
  const fade = useRef<{ start: number } | null>(null);
  useEffect(() => {
    const material = materialRef.current;
    if (!material) return;
    const u = material.uniforms;
    const next = frameTextureFrom(cacheRef.current, data, frame);
    const current = (u.mixT.value as number) >= 0.5 ? u.frameB.value : u.frameA.value;
    u.frameA.value = current ?? next;
    u.frameB.value = next;
    u.mixT.value = reducedMotion || !current ? 1 : 0;
    fade.current = reducedMotion ? null : { start: performance.now() };
    u.front.value = mask;
  }, [frame, mask, data, reducedMotion]);

  useEffect(() => {
    const material = materialRef.current;
    if (!material) return;
    material.uniforms.showAnomaly.value = layers.anomaly ? 1 : 0;
    material.uniforms.showEmergence.value = layers.emergence ? 1 : 0;
  }, [layers]);

  useFrame(() => {
    const material = materialRef.current;
    if (!material || !fade.current) return;
    const t = Math.min(1, (performance.now() - fade.current.start) / TIMELAPSE_FADE_MS);
    material.uniforms.mixT.value = t;
    if (t >= 1) fade.current = null;
  });

  const visible = layers.anomaly || layers.emergence;
  return (
    <group visible={visible}>
      <mesh raycast={noRaycast} renderOrder={RENDER_ORDER.timelapse}>
        <sphereGeometry args={[TIMELAPSE_RADIUS, EARTH_SEGMENTS, EARTH_SEGMENTS / 2]} />
        <shaderMaterial
          ref={materialRef}
          vertexShader={FIELD_VERTEX}
          fragmentShader={FIELD_FRAGMENT}
          uniforms={uniforms}
          transparent
          depthWrite={false}
        />
      </mesh>
      {layers.emergence ? (
        <>
          <FrontLine frame={emerged} data={data} direction={1} />
          <FrontLine frame={emerged} data={data} direction={-1} />
          {!reducedMotion && previousEmerged ? (
            <TimelapseRings key={year} data={data} frame={emerged} previous={previousEmerged} />
          ) : null}
        </>
      ) : null}
    </group>
  );
}
