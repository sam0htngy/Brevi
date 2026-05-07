
import { motion,  } from "framer-motion";
import useMousePosition from "../hooks/useMouseposition";

export default function Test(){
    const {x, y} = useMousePosition()

    return(
      <div style={{ minHeight: "100vh" }}>
        <motion.div
          style={{
            x,
            y,
            width: 40,
            height: 40,
            borderRadius: "50%",
            background: "red",
            position: "fixed",
            left: 0,
            top: 0,
            pointerEvents: "none",
            zIndex: 9999,
          }}
        />
      </div>
  )
}
