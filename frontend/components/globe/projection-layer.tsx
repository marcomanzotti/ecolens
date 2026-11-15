"use client";

import { useEffect, useMemo } from "react";
import { Color, DataTexture, NearestFilter, RGBAFormat, RepeatWrapping, ClampToEdgeWrapping, UnsignedByteType } from "three";

import type { ProjectionField, ProjectionMeta } from "@/lib/projections";
import { ROBUST_AGREEMENT_PCT } from "@/lib/projections";
import { EARTH_SEGMENTS, RENDER_ORDER, TIMELAPSE_RADIUS } from "./constants";
import { noRaycast } from "./markers";
import type { ProjectionLayerSpec } from "./projection-scales";
import { scaleBandIndex } from "./timelapse-datasets";
import { paletteTexture } from "./timelapse-textures";

const BYTE_MAX = 255;
const RGBA = 4;
const FIELD_OPACITY = 0.78;
const HATCH_DARK = "#07173F";
const HATCH_LIGHT = "#FFFFFF";

/**
 * One texel per 2° cell (rows south to north, as the sphere's UVs): R = colour band, G = has a
 * value, B = robust (at least 80% of models agree on the sign). Nearest filtering: each cell is
 * shown as the block it is, never smoothed.
 */
function fieldTexture(meta: ProjectionMeta, field: ProjectionField, spec: ProjectionLayerSpec): DataTexture {
  const { n_lat, n_lon } = meta.grid;
  const { scale } = meta.variables[field.variableId];
  const missing = meta.file_layout.missing_int16;
  const bytes = new Uint8Array(n_lat * n_lon * RGBA);
  for (let i = 0; i < n_lat * n_lon; i += 1) {
    const raw = field.median[i];
    if (raw === missing) continue;
    bytes[i * RGBA] = scaleBandIndex(spec.scale, raw * scale);
    bytes[i * RGBA + 1] = BYTE_MAX;
    bytes[i * RGBA + 2] = field.agreement[i] >= ROBUST_AGREEMENT_PCT ? BYTE_MAX : 0;
    bytes[i * RGBA + 3] = BYTE_MAX;
  }
  const texture = new DataTexture(bytes, n_lon, n_lat, RGBAFormat, UnsignedByteType);
  texture.magFilter = NearestFilter;
  texture.minFilter = NearestFilter;
  texture.wrapS = RepeatWrapping;
  texture.wrapT = ClampToEdgeWrapping;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
}

const VERTEX = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

// Colour = band of the median change; hatching = models disagree on the direction (< 80%).
const FRAGMENT = /* glsl */ `
  uniform sampler2D field;
  uniform sampler2D palette;
  uniform float bandCount;
  uniform float opacity;
  uniform vec3 hatchDark;
  uniform vec3 hatchLight;
  varying vec2 vUv;
  void main() {
    vec4 cell = texture2D(field, vUv);
    if (cell.g < 0.5) discard;
    float band = floor(cell.r * 255.0 + 0.5);
    vec3 color = texture2D(palette, vec2((band + 0.5) / bandCount, 0.5)).rgb;
    if (cell.b < 0.5) {
      float stripe = step(0.6, fract((gl_FragCoord.x - gl_FragCoord.y) / 6.0));
      float light = dot(color, vec3(0.2126, 0.7152, 0.0722));
      color = mix(color, light > 0.45 ? hatchDark : hatchLight, stripe * 0.7);
    }
    gl_FragColor = vec4(color, opacity);
    #include <colorspace_fragment>
  }
`;

interface ProjectionLayerProps {
  meta: ProjectionMeta;
  field: ProjectionField;
  spec: ProjectionLayerSpec;
}

/** The static "2050" map: CMIP6 median change, hatched where the models disagree. */
export function ProjectionLayer({ meta, field, spec }: ProjectionLayerProps) {
  const texture = useMemo(() => fieldTexture(meta, field, spec), [meta, field, spec]);
  useEffect(() => () => texture.dispose(), [texture]);
  const uniforms = useMemo(
    () => ({
      field: { value: texture },
      palette: { value: paletteTexture(spec.scale.bands) },
      bandCount: { value: spec.scale.bands.length },
      opacity: { value: FIELD_OPACITY },
      hatchDark: { value: new Color(HATCH_DARK) },
      hatchLight: { value: new Color(HATCH_LIGHT) },
    }),
    [texture, spec],
  );
  useEffect(() => () => uniforms.palette.value.dispose(), [uniforms]);
  return (
    <mesh raycast={noRaycast} renderOrder={RENDER_ORDER.timelapse}>
      <sphereGeometry args={[TIMELAPSE_RADIUS, EARTH_SEGMENTS, EARTH_SEGMENTS / 2]} />
      <shaderMaterial vertexShader={VERTEX} fragmentShader={FRAGMENT} uniforms={uniforms} transparent depthWrite={false} />
    </mesh>
  );
}
