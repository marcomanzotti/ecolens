/**
 * Shader of the time-lapse field. Every visual effect maps to a number from the data files:
 * colour = anomaly band (stepped, never smoothed between bands); hatching = no data that year in
 * a measured cell; transparent = a cell the dataset never measures;
 * glow = the one-cell band inside the emergence border; dimming = outside the significant area.
 * The year-to-year transition crossfades the colours of two real frames (`mixT`).
 */

export const FIELD_VERTEX = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

export const FIELD_FRAGMENT = /* glsl */ `
  uniform sampler2D frameA;
  uniform sampler2D frameB;
  uniform sampler2D front;
  uniform sampler2D palette;
  uniform float mixT;
  uniform float bandCount;
  uniform float minK;
  uniform float stepK;
  uniform float encodeRange;
  uniform float showAnomaly;
  uniform float showEmergence;
  uniform float fieldOpacity;
  uniform float notSignificantDim;
  uniform float areaFillOpacity;
  uniform float glowOpacity;
  uniform vec3 missingColor;
  uniform vec3 hatchColor;
  uniform vec3 warmingColor;
  uniform vec3 coolingColor;
  varying vec2 vUv;

  vec4 frameColor(sampler2D frame) {
    vec3 rgb = texture2D(frame, vUv).rgb;
    vec2 rg = rgb.rg;
    if (rgb.b < 0.5) return vec4(0.0);
    if (rg.g < 0.5) {
      float stripe = step(0.5, fract((gl_FragCoord.x + gl_FragCoord.y) / 7.0));
      return vec4(mix(missingColor, hatchColor, stripe), 1.0);
    }
    float k = rg.r / rg.g * 2.0 * encodeRange - encodeRange;
    float band = clamp(floor((k - minK) / stepK), 0.0, bandCount - 1.0);
    return vec4(texture2D(palette, vec2((band + 0.5) / bandCount, 0.5)).rgb, 1.0);
  }

  void main() {
    vec4 mask = texture2D(front, vUv);
    float significant = max(mask.b, mask.a);
    vec3 frontColor = mask.b > 0.5 ? warmingColor : coolingColor;
    float glow = max(mask.r, mask.g) * showEmergence;

    vec3 color = vec3(0.0);
    float alpha = 0.0;
    if (showAnomaly > 0.5) {
      vec4 field = mix(frameColor(frameA), frameColor(frameB), mixT);
      color = field.rgb;
      alpha = fieldOpacity * field.a;
      if (showEmergence > 0.5 && significant < 0.5) alpha *= notSignificantDim;
    } else if (showEmergence > 0.5 && significant > 0.5) {
      color = frontColor;
      alpha = areaFillOpacity;
    }
    color = mix(color, frontColor, glow * glowOpacity);
    alpha = max(alpha, glow * glowOpacity);
    if (alpha <= 0.0) discard;
    gl_FragColor = vec4(color, alpha);
    #include <colorspace_fragment>
  }
`;

export const RING_VERTEX = /* glsl */ `
  uniform float progress;
  uniform float startScale;
  uniform float endScale;
  varying vec3 vColor;
  void main() {
    vColor = instanceColor;
    float s = mix(startScale, endScale, progress);
    vec4 local = vec4(position.xy * s, position.z, 1.0);
    gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * local;
  }
`;

export const RING_FRAGMENT = /* glsl */ `
  uniform float progress;
  uniform float ringOpacity;
  varying vec3 vColor;
  void main() {
    gl_FragColor = vec4(vColor, ringOpacity * (1.0 - progress));
    #include <colorspace_fragment>
  }
`;
