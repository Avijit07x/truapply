const LESS_MOTION = "(prefers-reduced-motion: reduce)";

export function prefersLessMotion(): boolean {
  return window.matchMedia(LESS_MOTION).matches;
}
