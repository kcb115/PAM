import { useNavigate } from "react-router-dom";
import { Music, ArrowRight, Radio, MapPin, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.12, duration: 0.6, ease: "easeOut" },
  }),
};

export default function LandingPage({ user }) {
  const navigate = useNavigate();

  const handleStart = () => {
    if (user) {
      navigate("/dashboard");
    } else {
      navigate("/onboarding");
    }
  };

  return (
    <div className="hero-gradient min-h-screen relative overflow-hidden" data-testid="landing-page">
      {/* Ambient light spots */}
      <div className="absolute top-0 left-[20%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-[10%] w-[400px] h-[400px] bg-teal-500/4 rounded-full blur-[100px] pointer-events-none" />

      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-6 md:px-12 py-6">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-amber-500 flex items-center justify-center">
            <Music className="w-4 h-4 text-black" />
          </div>
          <span className="font-syne font-extrabold text-xl tracking-tight">PAM</span>
        </div>
        {user && (
          <Button
            variant="ghost"
            onClick={() => navigate("/dashboard")}
            className="text-sm text-zinc-400 hover:text-white"
            data-testid="go-to-dashboard-btn"
          >
            Dashboard
          </Button>
        )}
      </nav>

      {/* Hero */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 md:px-12 pt-20 md:pt-32 pb-20">
        <div className="max-w-3xl">
          <motion.p
            custom={0}
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            className="font-mono text-xs uppercase tracking-[0.2em] text-amber-500/80 mb-6"
            data-testid="hero-subtitle"
          >
            Concert Discovery Engine
          </motion.p>

          <motion.h1
            custom={1}
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            className="font-syne text-5xl md:text-7xl font-extrabold tracking-tight leading-[0.95] mb-8"
            data-testid="hero-title"
          >
            Find your next
            <br />
            <span className="text-amber-500">favorite show</span>
          </motion.h1>

          <motion.p
            custom={2}
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            className="text-lg md:text-xl text-zinc-400 leading-relaxed max-w-xl mb-12"
            data-testid="hero-description"
          >
            PAM analyzes your Spotify taste and discovers local concerts by
            independent artists you haven't heard yet — but will love.
          </motion.p>

          <motion.div
            custom={3}
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            className="flex flex-col sm:flex-row gap-4"
          >
            <Button
              onClick={handleStart}
              className="spotify-btn px-10 py-7 text-base"
              data-testid="get-started-btn"
            >
              <Sparkles className="w-5 h-5 mr-2" />
              {user ? "Go to Dashboard" : "Get Started"}
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </motion.div>
        </div>

        {/* Feature pills */}
        <motion.div
          custom={4}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="mt-24 grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          {[
            {
              icon: <Radio className="w-5 h-5 text-amber-500" />,
              title: "Taste Fingerprint",
              desc: "We build a deep profile from your top artists, genres, and audio preferences.",
            },
            {
              icon: <MapPin className="w-5 h-5 text-teal-500" />,
              title: "Local Discovery",
              desc: "Search concerts in your city. Filter by radius. Find hidden gems nearby.",
            },
            {
              icon: <Sparkles className="w-5 h-5 text-amber-500" />,
              title: "Smart Matching",
              desc: "Our algorithm scores every event against your taste. No noise, just signal.",
            },
          ].map((feature, i) => (
            <div
              key={i}
              className="glass-card p-6 group hover:border-white/10"
              data-testid={`feature-card-${i}`}
            >
              <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center mb-4 group-hover:bg-white/10 transition-colors duration-300">
                {feature.icon}
              </div>
              <h3 className="font-syne font-bold text-base mb-2">{feature.title}</h3>
              <p className="text-sm text-zinc-500 leading-relaxed">{feature.desc}</p>
            </div>
          ))}
        </motion.div>
      </div>

      {/* Footer */}
      <div className="relative z-10 border-t border-white/5 py-6 px-6 md:px-12">
        <p className="text-xs text-zinc-600 font-mono">
          PAM v1.0 — Powered by Spotify + Jambase
        </p>
      </div>
    </div>
  );
}
