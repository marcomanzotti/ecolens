/**
 * The Earth texture, equirectangular, left edge 180°W, top edge 90°N (the layout geo.ts assumes).
 * First choice: the Blue Marble shaded-relief image (NASA GIBS, static WebP files in
 * public/earth). Fallback when it cannot be loaded: a canvas drawn from Natural Earth outlines
 * (world-atlas) in brand colours.
 */
import { geoEquirectangular, geoGraticule, geoPath } from "d3-geo";
import type { GeometryObject, Topology } from "topojson-specification";
import { feature, mesh } from "topojson-client";
import { CanvasTexture, LinearMipmapLinearFilter, SRGBColorSpace, TextureLoader, type Texture } from "three";

import { GLOBE_COLORS } from "./colors";
import {
  BORDER_LINE_WIDTH,
  COAST_LINE_WIDTH,
  GRATICULE_LINE_WIDTH,
  GRATICULE_STEP_DEG,
  EARTH_IMAGE_URL,
  HUGE_TEXTURE_MIN_DEVICE_PX,
  SMALL_VIEWPORT_PX,
  TEXTURE_WIDTH_HUGE,
  TEXTURE_WIDTH_LARGE,
  TEXTURE_WIDTH_SMALL,
} from "./constants";

const FULL_TURN_RAD = 2 * Math.PI;
const ASPECT = 2;

async function loadAtlas(): Promise<Topology> {
  const atlas = await import("world-atlas/countries-50m.json");
  return atlas.default as unknown as Topology;
}

function paintEarth(context: CanvasRenderingContext2D, width: number, atlas: Topology): void {
  const height = width / ASPECT;
  const strokeScale = width / TEXTURE_WIDTH_LARGE;
  const projection = geoEquirectangular()
    .scale(width / FULL_TURN_RAD)
    .translate([width / 2, height / 2]);
  const path = geoPath(projection, context);
  const countries = atlas.objects.countries as GeometryObject;

  context.fillStyle = GLOBE_COLORS.ocean;
  context.fillRect(0, 0, width, height);

  context.beginPath();
  path(feature(atlas, countries));
  context.fillStyle = GLOBE_COLORS.land;
  context.fill();

  context.lineJoin = "round";
  context.beginPath();
  path(mesh(atlas, countries, (a, b) => a !== b));
  context.strokeStyle = GLOBE_COLORS.border;
  context.lineWidth = BORDER_LINE_WIDTH * strokeScale;
  context.stroke();

  context.beginPath();
  path(mesh(atlas, countries, (a, b) => a === b));
  context.strokeStyle = GLOBE_COLORS.coast;
  context.lineWidth = COAST_LINE_WIDTH * strokeScale;
  context.stroke();

  context.beginPath();
  path(geoGraticule().step([GRATICULE_STEP_DEG, GRATICULE_STEP_DEG])());
  context.strokeStyle = GLOBE_COLORS.graticule;
  context.lineWidth = GRATICULE_LINE_WIDTH * strokeScale;
  context.stroke();
}

/** Builds the texture. The caller owns it and must dispose of it. */
export async function createEarthTexture(width: number, anisotropy: number): Promise<CanvasTexture> {
  const atlas = await loadAtlas();
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = width / ASPECT;
  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("2D canvas is not available: cannot draw the Earth texture");
  }
  paintEarth(context, width, atlas);
  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  texture.anisotropy = anisotropy;
  texture.minFilter = LinearMipmapLinearFilter;
  return texture;
}

/** Loads one Blue Marble image. The caller owns the texture and must dispose of it. */
export async function loadEarthImage(width: number, anisotropy: number): Promise<Texture> {
  const texture = await new TextureLoader().loadAsync(EARTH_IMAGE_URL(width));
  texture.colorSpace = SRGBColorSpace;
  texture.anisotropy = anisotropy;
  texture.minFilter = LinearMipmapLinearFilter;
  return texture;
}

/**
 * Image widths to load, smallest first: the 2K image always comes first (fast), then one
 * upgrade chosen from the viewport and the GPU limit. Phones stay at 2K.
 */
export function earthImagePlan(viewportCssPx: number, devicePixelRatio: number, maxTextureSize: number): number[] {
  const plan = [TEXTURE_WIDTH_SMALL];
  if (viewportCssPx < SMALL_VIEWPORT_PX) return plan;
  const devicePx = viewportCssPx * devicePixelRatio;
  const wanted =
    devicePx >= HUGE_TEXTURE_MIN_DEVICE_PX && maxTextureSize >= TEXTURE_WIDTH_HUGE ? TEXTURE_WIDTH_HUGE : TEXTURE_WIDTH_LARGE;
  if (maxTextureSize >= wanted) plan.push(wanted);
  return plan;
}
