import { useEffect } from "react";
import { useMotionValue, useSpring } from "framer-motion";

interface MousePosition {
  x: ReturnType<typeof useSpring>;
  y: ReturnType<typeof useSpring>;
}

function useMousePosition(): MousePosition {
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const springConfig = { damping: 25, stiffness: 200, mass: 0.5 };
  const smoothX = useSpring(x, springConfig);
  const smoothY = useSpring(y, springConfig);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      x.set(e.clientX);
      y.set(e.clientY);
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [x, y]);

  return { x: smoothX, y: smoothY };
}

export default useMousePosition;
