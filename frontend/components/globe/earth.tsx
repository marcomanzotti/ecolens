"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useThree, type ThreeEvent } from "@react-three/fiber";
import { AdditiveBlending, BackSide, Color, Vector3, type ShaderMaterial, type Texture } from "three";

import { GLOBE_COLORS } from "./colors";
import {
  ATMOSPHERE_POWER,
  ATMOSPHERE_SCALE,
  ATMOSPHERE_STRENGTH,
  CLICK_MAX_TRAVEL_PX,
  EARTH_RADIUS,
  EARTH_SEGMENTS,
  NIGHT_LIGHT,
  OCEAN_SPECULAR_POWER,
  OCEAN_SPECULAR_STRENGTH,
  RIM_POWER,
  RIM_STRENGTH,
  SMALL_VIEWPORT_PX,
  SUN_DIRECTION_VIEW,
  TERMINATOR_SOFTNESS,
  TEXTURE_MAX_ANISOTROPY,
  TEXTURE_WIDTH_LARGE,
  TEXTURE_WIDTH_SMALL,
} from "./constants";
import { createEarthTexture, earthImagePlan, loadEarthImage } from "./earth-texture";
import { vec3ToRoundedLatLon, type LatLon } from "./geo";

const EARTH_VERTEX = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    vUv = uv;
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    vNormal = normalize(normalMatrix * normal);
    vView = normalize(-mvPosition.xyz);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

// Lighting is in view space, so the lit side always faces the viewer: the night side is the
// shaded edge of the disc, never hiding the data. Ocean = pixels where blue clearly dominates
// (the Blue Marble bathymetry), which is where the specular highlight goes.
const EARTH_FRAGMENT = /* glsl */ `
  uniform sampler2D map;
  uniform float hasMap;
  uniform vec3 ocean;
  uniform vec3 rim;
  uniform float rimPower;
  uniform float rimStrength;
  uniform vec3 sunDirection;
  uniform float nightLight;
  uniform float terminatorSoftness;
  uniform float specularStrength;
  uniform float specularPower;
  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    vec3 base = mix(ocean, texture2D(map, vUv).rgb, hasMap);
    vec3 n = normalize(vNormal);
    vec3 v = normalize(vView);
    vec3 l = normalize(sunDirection);
    float sunCos = dot(n, l);
    float day = smoothstep(-terminatorSoftness, terminatorSoftness, sunCos);
    float light = mix(nightLight, 1.0, day);
    float water = smoothstep(0.04, 0.16, base.b - max(base.r, base.g)) * hasMap;
    float specular = pow(max(dot(n, normalize(l + v)), 0.0), specularPower) * specularStrength * water * day;
    float edge = pow(1.0 - clamp(dot(n, v), 0.0, 1.0), rimPower);
    gl_FragColor = vec4(base * light + vec3(specular) + rim * edge * rimStrength * light, 1.0);
    #include <colorspace_fragment>
  }
`;

const ATMOSPHERE_FRAGMENT = /* glsl */ `
  uniform vec3 glow;
  uniform float limbCos;
  uniform float power;
  uniform float strength;
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    // Back faces: 0 at the outer edge of the shell, limbCos where the Earth's limb is.
    float depth = clamp(-dot(normalize(vNormal), normalize(vView)) / limbCos, 0.0, 1.0);
    float intensity = pow(depth, power) * strength;
    gl_FragColor = vec4(glow * intensity, intensity);
    #include <colorspace_fragment>
  }
`;

/** Cosine, at the Earth's limb, between the shell's normal and the line of sight. */
const ATMOSPHERE_LIMB_COS = Math.sqrt(1 - 1 / (ATMOSPHERE_SCALE * ATMOSPHERE_SCALE));

/**
 * The Blue Marble image, 2K first and then one sharper upgrade (earthImagePlan). If the first
 * image cannot be loaded, the outline drawing is used instead; if that fails too the globe stays
 * a plain ocean-coloured sphere (markers, picking and the layers still work).
 */
function useEarthTexture(): Texture | null {
  const gl = useThree((state) => state.gl);
  const [texture, setTexture] = useState<Texture | null>(null);

  useEffect(() => {
    let cancelled = false;
    let current: Texture | null = null;
    const anisotropy = Math.min(TEXTURE_MAX_ANISOTROPY, gl.capabilities.getMaxAnisotropy());
    const maxSize = gl.capabilities.maxTextureSize;
    const show = (next: Texture) => {
      if (cancelled) {
        next.dispose();
        return;
      }
      const previous = current;
      current = next;
      setTexture(next);
      // Free the smaller image only after the larger one is on screen.
      if (previous) requestAnimationFrame(() => previous.dispose());
    };
    const run = async () => {
      const [first, ...upgrades] = earthImagePlan(window.innerWidth, window.devicePixelRatio, maxSize);
      try {
        show(await loadEarthImage(first, anisotropy));
      } catch {
        const outlineWidth = Math.min(
          window.innerWidth < SMALL_VIEWPORT_PX ? TEXTURE_WIDTH_SMALL : TEXTURE_WIDTH_LARGE,
          maxSize,
        );
        show(await createEarthTexture(outlineWidth, anisotropy));
        return;
      }
      for (const width of upgrades) {
        if (cancelled) return;
        show(await loadEarthImage(width, anisotropy));
      }
    };
    // A failed upgrade keeps the image already shown; a failed fallback keeps the plain sphere.
    run().catch(() => undefined);
    return () => {
      cancelled = true;
      current?.dispose();
    };
  }, [gl]);

  return texture;
}

interface EarthProps {
  onPick: (point: LatLon) => void;
}

export function Earth({ onPick }: EarthProps) {
  const texture = useEarthTexture();
  const earthMaterialRef = useRef<ShaderMaterial>(null);
  const earthUniforms = useMemo(
    () => ({
      map: { value: null as Texture | null },
      hasMap: { value: 0 },
      ocean: { value: new Color(GLOBE_COLORS.ocean) },
      rim: { value: new Color(GLOBE_COLORS.rim) },
      rimPower: { value: RIM_POWER },
      rimStrength: { value: RIM_STRENGTH },
      sunDirection: { value: new Vector3(...SUN_DIRECTION_VIEW).normalize() },
      nightLight: { value: NIGHT_LIGHT },
      terminatorSoftness: { value: TERMINATOR_SOFTNESS },
      specularStrength: { value: OCEAN_SPECULAR_STRENGTH },
      specularPower: { value: OCEAN_SPECULAR_POWER },
    }),
    [],
  );
  const atmosphereUniforms = useMemo(
    () => ({
      glow: { value: new Color(GLOBE_COLORS.atmosphere) },
      limbCos: { value: ATMOSPHERE_LIMB_COS },
      power: { value: ATMOSPHERE_POWER },
      strength: { value: ATMOSPHERE_STRENGTH },
    }),
    [],
  );

  useEffect(() => {
    const material = earthMaterialRef.current;
    if (!material) return;
    material.uniforms.map.value = texture;
    material.uniforms.hasMap.value = texture ? 1 : 0;
  }, [texture]);

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    if (event.delta > CLICK_MAX_TRAVEL_PX) return;
    onPick(vec3ToRoundedLatLon(event.point.x, event.point.y, event.point.z));
  };
  // The Earth hides what is behind it: markers on the far side must not react.
  const block = (event: ThreeEvent<PointerEvent>) => event.stopPropagation();

  return (
    <>
      <mesh onClick={handleClick} onPointerOver={block} onPointerMove={block}>
        <sphereGeometry args={[EARTH_RADIUS, EARTH_SEGMENTS, EARTH_SEGMENTS / 2]} />
        <shaderMaterial
          ref={earthMaterialRef}
          vertexShader={EARTH_VERTEX}
          fragmentShader={EARTH_FRAGMENT}
          uniforms={earthUniforms}
        />
      </mesh>
      <mesh scale={ATMOSPHERE_SCALE} raycast={noRaycast}>
        <sphereGeometry args={[EARTH_RADIUS, EARTH_SEGMENTS, EARTH_SEGMENTS / 2]} />
        <shaderMaterial
          vertexShader={EARTH_VERTEX}
          fragmentShader={ATMOSPHERE_FRAGMENT}
          uniforms={atmosphereUniforms}
          side={BackSide}
          blending={AdditiveBlending}
          transparent
          depthWrite={false}
        />
      </mesh>
    </>
  );
}

/** The atmosphere is decoration: pointer rays go straight through it. */
function noRaycast(): void {}
