import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

export default function Toast({ message, onClose, duration = 4000 }) {
  useEffect(() => {
    if (!message) return;
    console.log("Toast displaying:", message);
    const timer = setTimeout(() => {
      console.log("Toast closing");
      onClose();
    }, duration);
    return () => clearTimeout(timer);
  }, [message, duration, onClose]);

  return (
    <AnimatePresence>
      {message && (
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          transition={{ type: "spring", stiffness: 300, damping: 25 }}
          className="fixed z-50 left-0 right-0 px-4"
          style={{
            bottom: "calc(env(safe-area-inset-bottom) + 7rem)",
            pointerEvents: "none"
          }}
        >
          <div className="max-w-md mx-auto">
            <div className="bg-gradient-to-br from-clay-500 to-clay-600 text-white rounded-2xl shadow-2xl p-4 border border-white/10">
              <div className="flex items-start gap-3">
                <motion.span
                  initial={{ scale: 0, rotate: -180 }}
                  animate={{ scale: 1, rotate: 0 }}
                  transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
                  className="text-2xl leading-none flex-shrink-0"
                >
                  ✨
                </motion.span>
                <p className="text-sm font-medium leading-relaxed flex-1">{message}</p>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
