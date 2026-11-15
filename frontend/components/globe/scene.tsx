"use client";

import { useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Stars } from "@react-three/drei";

import type { Location } from "@/lib/api";
import { CameraRig } from "./camera-rig";
import {
  CAMERA_FAR,
  CAMERA_FOV_DEG,
  CAMERA_NEAR,
  MAX_DEVICE_PIXEL_RATIO,
  STAR_COUNT,
  STAR_DEPTH,
  STAR_FACTOR,
  STAR_RADIUS,
} from "./constants";
import { Earth } from "./earth";
import type { LatLon } from "./geo";
import { PlaceMarkers, SelectedMarker } from "./markers";
import type { ProjectionField, ProjectionMeta } from "@/lib/projections";
import { ProjectionLayer } from "./projection-layer";
import { PROJECTION_LAYERS, type ProjectionLayerVariable } from "./projection-scales";
import type { TimelapseData } from "./timelapse-data";
import { TimelapseLayer, type TimelapseLayers } from "./timelapse-layer";
import { TrendLayer, TwinHighlight } from "./trend-layer";
import type { GlobeProps } from "./types";

/** Where the camera starts before the rig places it (it is moved on the first frame). */
const START_POSITION: [number, number, number] = [0, 0, 4];

export interface TimelapseScene {
  data: TimelapseData;
  year: number;
  layers: TimelapseLayers;
}

export interface GlobeSceneProps extends Omit<GlobeProps, "className" | "timelapse"> {
  /** The GISTEMP time-lapse to draw, if any (state lives in index.tsx). */
  timelapse: TimelapseScene | null;
  /** The static "2050" model projection, drawn instead of the time-lapse when set. */
  projection?: { meta: ProjectionMeta; field: ProjectionField } | null;
  /** A place focused in the accessible list: its marker is highlighted. */
  focusedPlaceId: string | null;
  reducedMotion: boolean;
  onContextLost: () => void;
}

/** The three.js part of the globe. Loaded on the client only (see index.tsx). */
export default function GlobeScene({
  places,
  selected,
  onSelect,
  trendMap,
  onCellSelect,
  highlightTwin,
  timelapse,
  projection = null,
  focusedPlaceId,
  reducedMotion,
  onContextLost,
}: GlobeSceneProps) {
  const [hoveredPlaceId, setHoveredPlaceId] = useState<string | null>(null);
  const [hoveringCell, setHoveringCell] = useState(false);
  const pointing = hoveredPlaceId !== null || hoveringCell;

  const handlePick = (point: LatLon) => onSelect({ lat: point.lat, lon: point.lon });
  const handleSelectPlace = (location: Location) => onSelect(location);

  return (
    <Canvas
      className="touch-none"
      style={{ cursor: pointing ? "pointer" : "grab" }}
      dpr={[1, MAX_DEVICE_PIXEL_RATIO]}
      flat
      camera={{ fov: CAMERA_FOV_DEG, near: CAMERA_NEAR, far: CAMERA_FAR, position: START_POSITION }}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      onCreated={({ gl }) => {
        gl.domElement.addEventListener("webglcontextlost", onContextLost, { once: true });
      }}
    >
      {/* Static starfield (speed 0): decoration only, it carries no data. */}
      <Stars radius={STAR_RADIUS} depth={STAR_DEPTH} count={STAR_COUNT} factor={STAR_FACTOR} saturation={0} fade speed={0} />
      <Earth onPick={handlePick} />
      {timelapse ? (
        <TimelapseLayer
          key={timelapse.data.dataset.id}
          data={timelapse.data}
          year={timelapse.year}
          layers={timelapse.layers}
          reducedMotion={reducedMotion}
        />
      ) : null}
      {projection ? (
        <ProjectionLayer
          meta={projection.meta}
          field={projection.field}
          spec={PROJECTION_LAYERS[projection.field.variableId as ProjectionLayerVariable]}
        />
      ) : null}
      {trendMap ? <TrendLayer map={trendMap} onCellSelect={onCellSelect} onHoverChange={setHoveringCell} /> : null}
      {trendMap && highlightTwin ? <TwinHighlight twin={highlightTwin} map={trendMap} /> : null}
      <PlaceMarkers
        places={places}
        highlightedId={hoveredPlaceId ?? focusedPlaceId}
        onSelect={handleSelectPlace}
        onHover={setHoveredPlaceId}
      />
      {selected ? <SelectedMarker location={selected} reducedMotion={reducedMotion} /> : null}
      <CameraRig
        focus={selected}
        box={trendMap?.bbox ?? null}
        autoRotate={!selected && !trendMap}
        reducedMotion={reducedMotion}
      />
    </Canvas>
  );
}
