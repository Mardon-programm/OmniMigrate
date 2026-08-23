import { useEffect, useRef, useState } from "react";

const easeOutExpo = (x: number): number => (x === 1 ? 1 : 1 - Math.pow(2, -10 * x));

/** Animate a number from its previous value to the new one (~700ms). */
export function useCountUp(target: number, duration = 700): number {
  const [display, setDisplay] = useState(target);
  const fromRef = useRef(target);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const from = fromRef.current;
    if (from === target) return;
    const start = performance.now();

    const tick = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      const value = from + (target - from) * easeOutExpo(progress);
      setDisplay(value);
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        fromRef.current = target;
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, duration]);

  return display;
}
