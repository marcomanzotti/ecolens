"use client";

import { useCallback, useEffect, useState } from "react";

/** Distance before the viewport at which a lazy block starts loading. */
const DEFAULT_MARGIN = "400px 0px";

/**
 * Becomes true the first time the element comes near the viewport, and stays true.
 * Used to start slow requests (the trend map) only when the visitor gets there.
 */
export function useSeenOnce<T extends Element>(
  rootMargin = DEFAULT_MARGIN,
): [(node: T | null) => void, boolean] {
  const [node, setNode] = useState<T | null>(null);
  const [seen, setSeen] = useState(false);
  const ref = useCallback((next: T | null) => setNode(next), []);

  useEffect(() => {
    if (seen || node === null) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) setSeen(true);
      },
      { rootMargin },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [node, seen, rootMargin]);

  return [ref, seen];
}
