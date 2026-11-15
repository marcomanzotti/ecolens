"use client";

import { useMemo, useRef } from "react";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { DoubleSide, Quaternion, Vector3, type Group, type Mesh, type MeshBasicMaterial } from "three";

import type { Location, Place } from "@/lib/api";
import { GLOBE_COLORS } from "./colors";
import {
  CLICK_MAX_TRAVEL_PX,
  MARKER_ALTITUDE,
  MARKER_HALO_FACTOR,
  MARKER_HIT_RADIUS,
  MARKER_HOVER_SCALE,
  MARKER_LAYER_GAP,
  MARKER_MAX_SCALE,
  MARKER_MIN_SCALE,
  MARKER_RADIUS,
  MARKER_REFERENCE_DISTANCE,
  MARKER_SEGMENTS,
  PULSE_MAX_SCALE,
  PULSE_OPACITY,
  PULSE_PERIOD_S,
  RENDER_ORDER,
  SELECTED_ALTITUDE,
  SELECTED_RING_INNER_FACTOR,
  SELECTED_RING_OUTER_FACTOR,
} from "./constants";
import { clamp, latLonToVec3 } from "./geo";
import { SceneLabel } from "./scene-label";

const FACING = new Vector3(0, 0, 1);

/** Position on the globe and the rotation that lays a flat shape on the surface there. */
function useSurfacePose(lat: number, lon: number, altitude: number) {
  return useMemo(() => {
    const position = latLonToVec3(lat, lon, altitude);
    const normal = new Vector3(...latLonToVec3(lat, lon));
    return { position, quaternion: new Quaternion().setFromUnitVectors(FACING, normal) };
  }, [lat, lon, altitude]);
}

/** Markers keep about the same size on screen whatever the zoom. */
function useScreenSizedScale(ref: React.RefObject<Group | null>, factor: number) {
  useFrame(({ camera }) => {
    const group = ref.current;
    if (!group) return;
    const altitude = camera.position.length() - 1;
    const scale = clamp(altitude / (MARKER_REFERENCE_DISTANCE - 1), MARKER_MIN_SCALE, MARKER_MAX_SCALE);
    group.scale.setScalar(scale * factor);
  });
}

interface PlaceMarkerProps {
  place: Place;
  highlighted: boolean;
  onSelect: (location: Location) => void;
  onHover: (placeId: string | null) => void;
}

function PlaceMarker({ place, highlighted, onSelect, onHover }: PlaceMarkerProps) {
  const groupRef = useRef<Group>(null);
  const pose = useSurfacePose(place.lat, place.lon, MARKER_ALTITUDE);
  useScreenSizedScale(groupRef, highlighted ? MARKER_HOVER_SCALE : 1);

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    if (event.delta > CLICK_MAX_TRAVEL_PX) return;
    onSelect({ lat: place.lat, lon: place.lon, label: place.name });
  };
  const handleOver = (event: ThreeEvent<PointerEvent>) => {
    event.stopPropagation();
    onHover(place.id);
  };

  return (
    <group position={pose.position} quaternion={pose.quaternion}>
      <group ref={groupRef}>
        <mesh onClick={handleClick} onPointerOver={handleOver} onPointerOut={() => onHover(null)} renderOrder={RENDER_ORDER.marker}>
          <circleGeometry args={[MARKER_HIT_RADIUS, MARKER_SEGMENTS]} />
          <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        </mesh>
        <mesh renderOrder={RENDER_ORDER.marker} raycast={noRaycast}>
          <circleGeometry args={[MARKER_RADIUS * MARKER_HALO_FACTOR, MARKER_SEGMENTS]} />
          <meshBasicMaterial color={GLOBE_COLORS.markerRing} transparent depthWrite={false} />
        </mesh>
        <mesh position-z={MARKER_LAYER_GAP} renderOrder={RENDER_ORDER.marker} raycast={noRaycast}>
          <circleGeometry args={[MARKER_RADIUS, MARKER_SEGMENTS]} />
          <meshBasicMaterial color={highlighted ? GLOBE_COLORS.selected : GLOBE_COLORS.marker} transparent depthWrite={false} />
        </mesh>
      </group>
      {highlighted ? <SceneLabel position={[0, 0, 0]} text={`${place.name}, ${place.country}`} /> : null}
    </group>
  );
}

interface PlaceMarkersProps {
  places: readonly Place[];
  highlightedId: string | null;
  onSelect: (location: Location) => void;
  onHover: (placeId: string | null) => void;
}

export function PlaceMarkers({ places, highlightedId, onSelect, onHover }: PlaceMarkersProps) {
  return (
    <>
      {places.map((place) => (
        <PlaceMarker
          key={place.id}
          place={place}
          highlighted={place.id === highlightedId}
          onSelect={onSelect}
          onHover={onHover}
        />
      ))}
    </>
  );
}

interface SelectedMarkerProps {
  location: Location;
  reducedMotion: boolean;
}

/** Neon ring on the place under investigation, with a slow pulse unless motion is reduced. */
export function SelectedMarker({ location, reducedMotion }: SelectedMarkerProps) {
  const groupRef = useRef<Group>(null);
  const pulseRef = useRef<Mesh>(null);
  const pulseMaterialRef = useRef<MeshBasicMaterial>(null);
  const pose = useSurfacePose(location.lat, location.lon, SELECTED_ALTITUDE);
  useScreenSizedScale(groupRef, 1);

  useFrame(({ clock }) => {
    const pulse = pulseRef.current;
    const material = pulseMaterialRef.current;
    if (!pulse || !material) return;
    pulse.visible = !reducedMotion;
    if (reducedMotion) return;
    const phase = (clock.elapsedTime % PULSE_PERIOD_S) / PULSE_PERIOD_S;
    pulse.scale.setScalar(1 + (PULSE_MAX_SCALE - 1) * phase);
    material.opacity = PULSE_OPACITY * (1 - phase);
  });

  const inner = MARKER_RADIUS * SELECTED_RING_INNER_FACTOR;
  const outer = MARKER_RADIUS * SELECTED_RING_OUTER_FACTOR;
  return (
    <group position={pose.position} quaternion={pose.quaternion}>
      <group ref={groupRef}>
        <mesh renderOrder={RENDER_ORDER.selected} raycast={noRaycast}>
          <ringGeometry args={[inner, outer, MARKER_SEGMENTS]} />
          <meshBasicMaterial color={GLOBE_COLORS.selected} side={DoubleSide} transparent depthWrite={false} />
        </mesh>
        <mesh renderOrder={RENDER_ORDER.selected} raycast={noRaycast}>
          <circleGeometry args={[MARKER_RADIUS, MARKER_SEGMENTS]} />
          <meshBasicMaterial color={GLOBE_COLORS.selected} transparent depthWrite={false} />
        </mesh>
        <mesh ref={pulseRef} renderOrder={RENDER_ORDER.selected} raycast={noRaycast}>
          <ringGeometry args={[inner, outer, MARKER_SEGMENTS]} />
          <meshBasicMaterial ref={pulseMaterialRef} color={GLOBE_COLORS.selected} side={DoubleSide} transparent depthWrite={false} />
        </mesh>
      </group>
    </group>
  );
}

/** Decorative parts: pointer rays go through them to the hit area or the Earth. */
export function noRaycast(): void {}

