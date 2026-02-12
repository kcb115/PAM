import { motion } from "framer-motion";

export const LoadingState = ({ type }) => {
  const messages = {
    taste: [
      "Analyzing your top artists...",
      "Mapping genre connections...",
      "Building your sound fingerprint...",
    ],
    discover: [
      "Searching local events...",
      "Matching artists to your taste...",
      "Scoring & ranking concerts...",
    ],
  };

  const texts = messages[type] || messages.taste;

  return (
    <div
      className="fixed inset-0 z-[60] bg-black/80 backdrop-blur-sm flex items-center justify-center"
      data-testid="loading-overlay"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-card p-10 max-w-sm w-full mx-4 text-center"
      >
        {/* Equalizer animation */}
        <div className="flex items-end justify-center gap-1.5 h-10 mb-8">
          <div className="eq-bar eq-bar-1" />
          <div className="eq-bar eq-bar-2" />
          <div className="eq-bar eq-bar-3" />
          <div className="eq-bar eq-bar-4" />
          <div className="eq-bar eq-bar-5" />
          <div className="eq-bar eq-bar-3" />
          <div className="eq-bar eq-bar-1" />
        </div>

        <div className="space-y-2">
          {texts.map((text, i) => (
            <motion.p
              key={text}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 1.2, duration: 0.5 }}
              className="font-mono text-xs text-zinc-400"
            >
              {text}
            </motion.p>
          ))}
        </div>

        <div className="mt-6 flex justify-center gap-1">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-[#DED5EB] pulse-dot"
              style={{ animationDelay: `${i * 0.3}s` }}
            />
          ))}
        </div>
      </motion.div>
    </div>
  );
};
