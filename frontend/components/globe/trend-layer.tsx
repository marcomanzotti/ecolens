"use client";

import { useEffect, useMemo, useState } from "react";
import type { ThreeEvent } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import { BufferAttribute, BufferGeometry } from "three";

import type { OppositeTwin, TrendMapCell, TrendMapResult } from "@/lib/api";
import { GLOBE_COLORS } from "./colors";
import {
  CLICK_MAX_TRAVEL_PX,
  RENDER_ORDER,
  TREND_MAX_QUAD_DEG,
  TREND_OUTLINE_OPACITY,
  TREND_OUTLINE_RADIUS,
  TREND_OUTLINE_WIDTH_PX,
  TREND_RADIUS,
  TWIN_ARC_LIFT_PER_RAD,
  TWIN_ARC_MAX_LIFT,
  TWIN_ARC_MIN_LIFT,
  TWIN_ARC_SEGMENTS,
  TWIN_LINE_WIDTH_PX,
  TWIN_RADIUS,
} from "./constants";
import { angularDistance, clamp, greatCircleArc, latLonToVec3, type Vec3 } from "./geo";
import { noRaycast } from "./markers";
import { SceneLabel } from "./scene-label";
import { buildTrendGeometry, cellOutline, maxAbsSlope } from "./trend-geometry";
import { cellLabel } from "./trend-summary";

const POSITION_SIZE = 3;
const COLOR_SIZE = 4;

function useTrendGeometries(map: TrendMapResult) {
  const built = useMemo(() => {
    const maxAbs = map.summary.max_abs_slope > 0 ? map.summary.max_abs_slope : maxAbsSlope(map.cells);
    const data = buildTrendGeometry(map.cells, map.grid, {
      radius: TREND_RADIUS,
      outlineRadius: TREND_OUTLINE_RADIUS,
      maxQuadDeg: TREND_MAX_QUAD_DEG,
      maxAbs,
    });
    const cells = new BufferGeometry();
    cells.setAttribute("position", new BufferAttribute(data.positions, POSITION_SIZE));
    cells.setAttribute("color", new BufferAttribute(data.colors, COLOR_SIZE));
    cells.setIndex(new BufferAttribute(data.indices, 1));
    cells.computeBoundingSphere();
    const outline: Vec3[] = [];
    for (let i = 0; i < data.outline.length; i += POSITION_SIZE) {
      outline.push([data.outline[i], data.outline[i + 1], data.outline[i + 2]]);
    }
    return { cells, outline, faceCell: data.faceCell };
  }, [map]);

  useEffect(
    () => () => {
      built.cells.dispose();
    },
    [built],
  );
  return built;
}

interface TrendLayerProps {
  map: TrendMapResult;
  onCellSelect?: (cell: TrendMapCell) => void;
  onHoverChange: (hovering: boolean) => void;
}

/** Every cell of the map in one merged mesh, coloured by slope; significant areas outlined. */
export function TrendLayer({ map, onCellSelect, onHoverChange }: TrendLayerProps) {
  const { cells, outline, faceCell } = useTrendGeometries(map);
  const [hovered, setHovered] = useState<number | null>(null);

  const cellAt = (faceIndex: number | null | undefined): number | null => {
    if (faceIndex === null || faceIndex === undefined) return null;
    const index = faceCell[faceIndex];
    return index === undefined ? null : index;
  };

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    // Without a handler, clicks fall through to the Earth and pick a point.
    if (!onCellSelect) return;
    event.stopPropagation();
    if (event.delta > CLICK_MAX_TRAVEL_PX) return;
    const index = cellAt(event.faceIndex);
    if (index !== null) onCellSelect(map.cells[index]);
  };
  const handleMove = (event: ThreeEvent<PointerEvent>) => {
    event.stopPropagation();
    setHovered(cellAt(event.faceIndex));
    onHoverChange(Boolean(onCellSelect));
  };
  const handleOut = () => {
    setHovered(null);
    onHoverChange(false);
  };

  const hoveredCell = hovered === null ? null : map.cells[hovered];
  return (
    <>
      <mesh
        geometry={cells}
        renderOrder={RENDER_ORDER.trend}
        onClick={handleClick}
        onPointerMove={handleMove}
        onPointerOut={handleOut}
      >
        <meshBasicMaterial vertexColors transparent depthWrite={false} />
      </mesh>
      {outline.length > 0 ? (
        <Line
          points={outline}
          segments
          color={GLOBE_COLORS.significantOutline}
          lineWidth={TREND_OUTLINE_WIDTH_PX}
          transparent
          opacity={TREND_OUTLINE_OPACITY}
          depthWrite={false}
          renderOrder={RENDER_ORDER.outline}
          raycast={noRaycast}
        />
      ) : null}
      {hoveredCell ? (
        <SceneLabel
          position={latLonToVec3(hoveredCell.lat, hoveredCell.lon, TREND_OUTLINE_RADIUS)}
          text={cellLabel(hoveredCell, map.variable.unit)}
        />
      ) : null}
    </>
  );
}

interface TwinHighlightProps {
  twin: OppositeTwin;
  map: TrendMapResult;
}

/** The rising and the falling twin outlined in neon, joined by an arc. */
export function TwinHighlight({ twin, map }: TwinHighlightProps) {
  const lines = useMemo(() => {
    const lift = clamp(angularDistance(twin.up, twin.down) * TWIN_ARC_LIFT_PER_RAD, TWIN_ARC_MIN_LIFT, TWIN_ARC_MAX_LIFT);
    return {
      arc: greatCircleArc(twin.up, twin.down, TWIN_ARC_SEGMENTS, TWIN_RADIUS, lift),
      up: cellOutline(twin.up, map.grid, TWIN_RADIUS, TREND_MAX_QUAD_DEG),
      down: cellOutline(twin.down, map.grid, TWIN_RADIUS, TREND_MAX_QUAD_DEG),
    };
  }, [twin, map.grid]);

  const common = {
    color: GLOBE_COLORS.twin,
    lineWidth: TWIN_LINE_WIDTH_PX,
    transparent: true,
    depthWrite: false,
    renderOrder: RENDER_ORDER.twin,
    raycast: noRaycast,
  };
  return (
    <>
      <Line points={lines.arc} {...common} />
      <Line points={lines.up} {...common} />
      <Line points={lines.down} {...common} />
    </>
  );
}
