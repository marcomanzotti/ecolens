/** Tunables of the globe scene. The Earth is a unit sphere centred on the origin. */

export const EARTH_RADIUS = 1;
export const EARTH_SEGMENTS = 96;

export const CAMERA_FOV_DEG = 40;
export const CAMERA_NEAR = 0.05;
export const CAMERA_FAR = 50;
/** Extra room around the globe when it is shown whole (1 = touching the edges). */
export const FIT_MARGIN = 1.18;
/** How far out the user may zoom, relative to the distance that shows the whole globe. */
export const MAX_DISTANCE_FACTOR = 1.25;
export const MIN_DISTANCE = 1.12;
/** Share of the view a trend-map box should fill after the camera flies to it. */
export const BOX_VIEW_FILL = 0.62;
/** OrbitControls cannot look straight down a pole: stay a little short of it. */
export const MAX_CAMERA_LAT_DEG = 85;
export const INITIAL_VIEW = { lat: 18, lon: 12 } as const;

export const MAX_DEVICE_PIXEL_RATIO = 2;

export const FLY_DURATION_S = 1.1;
export const AUTO_ROTATE_RAD_PER_S = 0.05;
/** Longest time step taken into account, so a frame after a long idle does not jump. */
export const MAX_FRAME_DELTA_S = 0.05;
export const BASE_ROTATE_SPEED = 0.6;
export const DAMPING_FACTOR = 0.12;

/** Pointer travel (px) between press and release above which a click is a drag. */
export const CLICK_MAX_TRAVEL_PX = 6;

export const TREND_RADIUS = 1.002;
/** Cells larger than this many degrees are subdivided so they follow the sphere. */
export const TREND_MAX_QUAD_DEG = 2;

export const MARKER_ALTITUDE = 1.004;
export const MARKER_RADIUS = 0.014;
export const MARKER_HIT_RADIUS = 0.05;
/** Camera distance at which markers have their nominal size. */
export const MARKER_REFERENCE_DISTANCE = 3.4;
export const MARKER_MIN_SCALE = 0.08;
export const MARKER_MAX_SCALE = 1.6;
export const PULSE_PERIOD_S = 1.8;

export const TWIN_RADIUS = 1.006;
export const TWIN_ARC_SEGMENTS = 48;
export const TWIN_LINE_WIDTH_PX = 3;

export const ATMOSPHERE_SCALE = 1.16;

export const TEXTURE_WIDTH_LARGE = 4096;
export const TEXTURE_WIDTH_SMALL = 2048;
/** Largest Earth image: only on wide, dense screens whose GPU accepts it. */
export const TEXTURE_WIDTH_HUGE = 8192;
/** Screen width in device pixels (CSS width x devicePixelRatio) from which the 8K image is used. */
export const HUGE_TEXTURE_MIN_DEVICE_PX = 2560;
/** Blue Marble shaded relief from NASA GIBS, built by scripts/build_earth_assets.py. */
export const EARTH_IMAGE_URL = (width: number) => `/earth/bluemarble-${width}.webp`;

/** Earth shading. The light comes from the viewer's upper left, so the facing side is lit. */
export const SUN_DIRECTION_VIEW: readonly [number, number, number] = [-0.55, 0.45, 0.7];
/** Brightness kept on the night side, so that the data drawn there stays readable. */
export const NIGHT_LIGHT = 0.28;
/** Width of the day-night transition (in cosine of the sun angle). */
export const TERMINATOR_SOFTNESS = 0.35;
export const OCEAN_SPECULAR_STRENGTH = 0.35;
export const OCEAN_SPECULAR_POWER = 48;

export const STAR_RADIUS = 22;
export const STAR_DEPTH = 18;
export const STAR_COUNT = 2600;
export const STAR_FACTOR = 2.2;
/** Viewports narrower than this (CSS px) get the smaller Earth texture. */
export const SMALL_VIEWPORT_PX = 768;
export const GRATICULE_STEP_DEG = 15;

/** Stroke widths on the Earth texture, in pixels of a TEXTURE_WIDTH_LARGE texture. */
export const COAST_LINE_WIDTH = 1.6;
export const BORDER_LINE_WIDTH = 1;
export const GRATICULE_LINE_WIDTH = 1;
export const TEXTURE_MAX_ANISOTROPY = 8;

/** Atmosphere glow: falls from the limb of the Earth to the edge of the shell. */
export const ATMOSPHERE_POWER = 2.2;
export const ATMOSPHERE_STRENGTH = 0.85;
/** Light rim painted on the Earth itself near its limb. */
export const RIM_POWER = 3;
export const RIM_STRENGTH = 0.55;

/** Draw order of the see-through layers (higher is drawn later, on top). */
export const RENDER_ORDER = {
  timelapse: 1,
  trend: 1,
  front: 2,
  outline: 2,
  ring: 3,
  twin: 3,
  marker: 4,
  selected: 5,
} as const;

/** Time-lapse layers (GISTEMP), just above the Earth and below the markers. */
export const TIMELAPSE_RADIUS = 1.0015;
export const TIMELAPSE_FRONT_RADIUS = 1.0025;
export const TIMELAPSE_RING_RADIUS = 1.003;
/** Fixed playback speed: one year every 0.6 s. */
export const TIMELAPSE_YEAR_MS = 600;
/** Years too early for a trend test (record shorter than the minimum) pass faster. */
export const TIMELAPSE_UNTESTED_YEAR_MS = 180;
/** Linear crossfade between two real yearly frames (shorter than a year step). */
export const TIMELAPSE_FADE_MS = 300;
/** Life of the ring a cell emits in the year its trend becomes significant. */
export const TIMELAPSE_RING_MS = 800;
/** Ring radius at the end of its life, in cells (one cell = 2 degrees). */
export const TIMELAPSE_RING_MAX_CELLS = 2.5;
/** Opacity of a ring when it is emitted; it fades linearly to 0. */
export const TIMELAPSE_RING_OPACITY = 0.6;
export const TIMELAPSE_FIELD_OPACITY = 0.66;
/** Opacity of cells outside the significant area while the emergence layer is on. */
export const TIMELAPSE_NOT_SIGNIFICANT_DIM = 0.45;
/** Fill of the significant area when the anomaly field is off. */
export const TIMELAPSE_AREA_FILL_OPACITY = 0.28;
/** Glow inside the border: exactly one grid cell wide. */
export const TIMELAPSE_GLOW_OPACITY = 0.55;
export const TIMELAPSE_FRONT_WIDTH_PX = 1.6;

export const TREND_OUTLINE_RADIUS = 1.003;
export const TREND_OUTLINE_OPACITY = 0.95;
export const TREND_OUTLINE_WIDTH_PX = 1.5;

export const MARKER_SEGMENTS = 32;
/** Marker parts, as multiples of MARKER_RADIUS. */
export const MARKER_HALO_FACTOR = 1.7;
export const MARKER_HOVER_SCALE = 1.35;
/** Gap between the stacked flat parts of a marker, so they do not z-fight. */
export const MARKER_LAYER_GAP = 0.0015;
export const SELECTED_ALTITUDE = 1.008;
export const SELECTED_RING_INNER_FACTOR = 1.9;
export const SELECTED_RING_OUTER_FACTOR = 2.6;
/** How far the pulse ring grows (multiple of its resting size) before it fades out. */
export const PULSE_MAX_SCALE = 2.4;
export const PULSE_OPACITY = 0.7;

/** Lift of the twin arc at its middle, per radian of distance between the cells. */
export const TWIN_ARC_LIFT_PER_RAD = 0.35;
export const TWIN_ARC_MIN_LIFT = 0.004;
export const TWIN_ARC_MAX_LIFT = 0.25;

/** Offset (CSS px) of the floating labels above the point they describe. */
export const LABEL_OFFSET_PX = 14;
