"use client";

import { useEffect, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";

import {
  AUTO_ROTATE_RAD_PER_S,
  BASE_ROTATE_SPEED,
  BOX_VIEW_FILL,
  CAMERA_FOV_DEG,
  DAMPING_FACTOR,
  FIT_MARGIN,
  FLY_DURATION_S,
  INITIAL_VIEW,
  MAX_CAMERA_LAT_DEG,
  MAX_DISTANCE_FACTOR,
  MAX_FRAME_DELTA_S,
  MIN_DISTANCE,
} from "./constants";
import {
  boxAngularRadius,
  boxCenter,
  capViewDistance,
  clamp,
  degToRad,
  easeInOutCubic,
  fitDistance,
  vec3ToLatLon,
  writeInterpolatedView,
  writeLatLonToVec3,
  type GeoBox,
  type LatLon,
  type MutableVec3,
} from "./geo";

const MIN_POLAR_ANGLE = degToRad(90 - MAX_CAMERA_LAT_DEG);
const MAX_POLAR_ANGLE = Math.PI - MIN_POLAR_ANGLE;

interface FlightRequest {
  lat: number;
  lon: number;
  /** Angular radius of what must fit the view, or null to keep the current zoom. */
  capRadius: number | null;
}

interface RigState {
  /** Distance that shows the whole globe at the current aspect ratio, once known. */
  fit: number | null;
  request: FlightRequest | null;
  flying: boolean;
  progress: number;
  from: LatLon;
  to: LatLon;
  fromDistance: number;
  toDistance: number;
  view: LatLon;
  position: MutableVec3;
  userHasInteracted: boolean;
}

function createRigState(): RigState {
  return {
    fit: null,
    request: null,
    flying: false,
    progress: 0,
    from: { lat: 0, lon: 0 },
    to: { lat: 0, lon: 0 },
    fromDistance: 0,
    toDistance: 0,
    view: { lat: 0, lon: 0 },
    position: [0, 0, 0],
    userHasInteracted: false,
  };
}

interface CameraRigProps {
  /** Where to look: the camera flies there whenever the coordinates change. */
  focus: LatLon | null;
  /** A box to frame: the camera flies to it whenever it changes. */
  box: GeoBox | null;
  /** Whether the globe may turn by itself (until the user first touches it). */
  autoRotate: boolean;
  reducedMotion: boolean;
}

/** Owns the camera: user orbiting, fitting the globe to the view, flights, idle rotation. */
export function CameraRig({ focus, box, autoRotate, reducedMotion }: CameraRigProps) {
  const controlsRef = useRef<OrbitControlsImpl>(null);
  const rigRef = useRef<RigState | null>(null);
  if (rigRef.current === null) {
    rigRef.current = createRigState();
  }

  const boxLatMin = box?.lat_min;
  const boxLatMax = box?.lat_max;
  const boxLonMin = box?.lon_min;
  const boxLonMax = box?.lon_max;
  useEffect(() => {
    const rig = rigRef.current;
    if (!rig || boxLatMin === undefined || boxLatMax === undefined || boxLonMin === undefined || boxLonMax === undefined) {
      return;
    }
    const target = { lat_min: boxLatMin, lat_max: boxLatMax, lon_min: boxLonMin, lon_max: boxLonMax };
    rig.request = { ...boxCenter(target), capRadius: boxAngularRadius(target) };
  }, [boxLatMin, boxLatMax, boxLonMin, boxLonMax]);

  const focusLat = focus?.lat;
  const focusLon = focus?.lon;
  useEffect(() => {
    const rig = rigRef.current;
    if (!rig || focusLat === undefined || focusLon === undefined) return;
    // A pending box framing wins: on mount both effects fire, and the box must keep its zoom.
    if (rig.request && rig.request.capRadius !== null) return;
    rig.request = { lat: focusLat, lon: focusLon, capRadius: null };
  }, [focusLat, focusLon]);

  useFrame((state, delta) => {
    const rig = rigRef.current;
    const controls = controlsRef.current;
    if (!rig || !controls) return;
    const camera = state.camera;
    const aspect = state.size.width / Math.max(1, state.size.height);
    const fit = fitDistance(CAMERA_FOV_DEG, aspect, FIT_MARGIN);

    if (rig.fit === null) {
      writeLatLonToVec3(rig.position, INITIAL_VIEW.lat, INITIAL_VIEW.lon, fit);
      camera.position.set(rig.position[0], rig.position[1], rig.position[2]);
      camera.lookAt(0, 0, 0);
    } else if (rig.fit !== fit) {
      // The container changed shape: keep the same relative zoom.
      camera.position.multiplyScalar(fit / rig.fit);
      rig.toDistance *= fit / rig.fit;
      rig.fromDistance *= fit / rig.fit;
    }
    rig.fit = fit;
    controls.maxDistance = fit * MAX_DISTANCE_FACTOR;

    if (rig.request) {
      const request = rig.request;
      rig.request = null;
      const distance = camera.position.length();
      const here = vec3ToLatLon(camera.position.x, camera.position.y, camera.position.z);
      rig.from.lat = here.lat;
      rig.from.lon = here.lon;
      rig.to.lat = clamp(request.lat, -MAX_CAMERA_LAT_DEG, MAX_CAMERA_LAT_DEG);
      rig.to.lon = request.lon;
      rig.fromDistance = distance;
      const wanted =
        request.capRadius === null
          ? Math.min(distance, fit)
          : capViewDistance(request.capRadius, CAMERA_FOV_DEG, aspect, BOX_VIEW_FILL);
      rig.toDistance = clamp(wanted, MIN_DISTANCE, fit);
      rig.progress = reducedMotion ? 1 : 0;
      rig.flying = true;
    }

    const step = Math.min(delta, MAX_FRAME_DELTA_S);
    if (rig.flying) {
      rig.progress = Math.min(1, rig.progress + step / FLY_DURATION_S);
      const eased = easeInOutCubic(rig.progress);
      writeInterpolatedView(rig.view, rig.from, rig.to, eased);
      const distance = rig.fromDistance + (rig.toDistance - rig.fromDistance) * eased;
      writeLatLonToVec3(rig.position, rig.view.lat, rig.view.lon, distance);
      camera.position.set(rig.position[0], rig.position[1], rig.position[2]);
      camera.lookAt(0, 0, 0);
      rig.flying = rig.progress < 1;
    } else if (autoRotate && !reducedMotion && !rig.userHasInteracted) {
      const angle = AUTO_ROTATE_RAD_PER_S * step;
      const cos = Math.cos(angle);
      const sin = Math.sin(angle);
      const { x, z } = camera.position;
      // Turning the camera eastwards about the axis makes the Earth appear to spin west to east.
      camera.position.x = x * cos + z * sin;
      camera.position.z = z * cos - x * sin;
      camera.lookAt(0, 0, 0);
    }

    // Slower orbiting when close, so a drag moves the surface about as far as the pointer.
    const altitude = camera.position.length() - 1;
    controls.rotateSpeed = BASE_ROTATE_SPEED * clamp(altitude / (fit - 1), 0, 1);
  });

  const handleStart = () => {
    const rig = rigRef.current;
    if (!rig) return;
    rig.userHasInteracted = true;
    rig.flying = false;
  };

  return (
    <OrbitControls
      ref={controlsRef}
      makeDefault
      enablePan={false}
      enableDamping
      dampingFactor={DAMPING_FACTOR}
      minDistance={MIN_DISTANCE}
      minPolarAngle={MIN_POLAR_ANGLE}
      maxPolarAngle={MAX_POLAR_ANGLE}
      onStart={handleStart}
    />
  );
}
