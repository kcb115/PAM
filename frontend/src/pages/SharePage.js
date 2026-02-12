import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Music, Zap, Waves, Heart, Gauge, Piano, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { api } from "@/lib/api";

export default function SharePage() {
  const { shareId } = useParams();
  const navigate = useNavigate();
  const [share, setShare] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (shareId) {
      api.getShare(shareId)
        .then((res) => setShare(res.data))
        .catch(() => setError("This taste profile link is invalid or expired."))
        .finally(() => setLoading(false));
    }
  }, [shareId]);

  if (loading) {
    return (
      <div className="hero-gradient min-h-screen flex items-center justify-center">
        <div className="flex items-end gap-1.5 h-10">
          <div className="eq-bar eq-bar-1" />
          <div className="eq-bar eq-bar-2" />
          <div className="eq-bar eq-bar-3" />
          <div className="eq-bar eq-bar-4" />
          <div className="eq-bar eq-bar-5" />
        </div>
      </div>
    );
  }

  if (error || !share) {
    return (
      <div className="hero-gradient min-h-screen flex items-center justify-center" data-testid="share-error">
        <div className="text-center">
          <p className="text-zinc-400 mb-4">{error || "Profile not found."}</p>
          <Button
            onClick={() => navigate("/")}
            className="bg-[#380E75] text-[#DED5EB] font-syne font-bold rounded-full px-8 py-6"
          >
            Discover Your Taste
          </Button>
        </div>
      </div>
    );
  }

  const radarData = [
    { label: "Energy", value: share.audio_features?.energy || 0 },
    { label: "Dance", value: share.audio_features?.danceability || 0 },
    { label: "Mood", value: share.audio_features?.valence || 0 },
    { label: "Acoustic", value: share.audio_features?.acousticness || 0 },
    { label: "Instrumental", value: share.audio_features?.instrumentalness || 0 },
  ];

  const topRootGenres = Object.entries(share.root_genre_map || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  const featureLabels = {
    energy: { icon: <Zap className="w-4 h-4" />, label: "Energy" },
    danceability: { icon: <Waves className="w-4 h-4" />, label: "Dance" },
    valence: { icon: <Heart className="w-4 h-4" />, label: "Mood" },
    acousticness: { icon: <Piano className="w-4 h-4" />, label: "Acoustic" },
    instrumentalness: { icon: <Gauge className="w-4 h-4" />, label: "Instrumental" },
  };

  return (
    <div className="hero-gradient min-h-screen" data-testid="share-page">
      {/* Ambient lights */}
      <div className="absolute top-0 left-[20%] w-[500px] h-[500px] bg-[#380E75]/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-[10%] w-[400px] h-[400px] bg-[#DED5EB]/4 rounded-full blur-[100px] pointer-events-none" />

      <nav className="relative z-10 flex items-center justify-between px-6 md:px-12 py-6">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate("/")}>
          <div className="w-8 h-8 rounded-lg bg-[#380E75] flex items-center justify-center">
            <Music className="w-4 h-4 text-[#DED5EB]" />
          </div>
          <span className="font-syne font-extrabold text-xl tracking-tight">PAM</span>
        </div>
      </nav>

      <div className="relative z-10 max-w-2xl mx-auto px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          {/* Header */}
          <div className="text-center mb-10">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-[#DED5EB]/80 mb-3">
              Taste Profile
            </p>
            <h1 className="font-syne text-4xl md:text-5xl font-extrabold tracking-tight mb-3">
              {share.user_name}'s
              <br />
              <span className="text-[#DED5EB]">Sound DNA</span>
            </h1>
            <p className="text-zinc-500 text-sm">
              Based on {share.top_artist_count} top artists
            </p>
          </div>

          {/* Radar Chart */}
          <div className="glass-card p-8 mb-6">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="75%">
                  <PolarGrid stroke="rgba(255,255,255,0.06)" />
                  <PolarAngleAxis
                    dataKey="label"
                    tick={{ fill: "#a1a1aa", fontSize: 12, fontFamily: "JetBrains Mono" }}
                  />
                  <Radar
                    dataKey="value"
                    stroke="#DED5EB"
                    fill="#380E75"
                    fillOpacity={0.25}
                    strokeWidth={2}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            {/* Audio feature bars */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-6">
              {Object.entries(share.audio_features || {}).map(([key, val]) => {
                if (key === "tempo") return null;
                const info = featureLabels[key];
                if (!info) return null;
                return (
                  <div key={key} className="flex items-center gap-2">
                    <span className="text-[#DED5EB]">{info.icon}</span>
                    <div className="flex-1">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-zinc-400">{info.label}</span>
                        <span className="font-mono text-zinc-500">{Math.round(val * 100)}%</span>
                      </div>
                      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-[#DED5EB]"
                          style={{ width: `${Math.round(val * 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Genre DNA */}
          <div className="glass-card p-8 mb-6">
            <p className="font-mono text-xs uppercase tracking-[0.15em] text-zinc-500 mb-4">
              Genre DNA
            </p>
            <div className="space-y-3 mb-6">
              {topRootGenres.map(([genre, weight]) => (
                <div key={genre} className="flex items-center gap-3">
                  <span className="font-jakarta text-sm text-zinc-300 w-28 truncate capitalize">
                    {genre}
                  </span>
                  <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.round(weight * 100)}%`,
                        background: weight > 0.6 ? "#DED5EB" : weight > 0.3 ? "#380E75" : "#3f3f46",
                      }}
                    />
                  </div>
                  <span className="font-mono text-xs text-zinc-600 w-10 text-right">
                    {Math.round(weight * 100)}%
                  </span>
                </div>
              ))}
            </div>

            {/* Genre tags */}
            <div className="flex flex-wrap gap-2">
              {(share.top_genres || []).map((genre) => (
                <Badge
                  key={genre}
                  variant="secondary"
                  className="text-xs font-mono border border-white/10 bg-white/5 text-zinc-400"
                >
                  {genre}
                </Badge>
              ))}
            </div>
          </div>

          {/* CTA */}
          <div className="text-center">
            <Button
              onClick={() => navigate("/onboarding")}
              className="spotify-btn px-10 py-7 text-base"
              data-testid="share-cta-btn"
            >
              Discover Your Taste
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
            <p className="text-xs text-zinc-600 mt-4 font-mono">
              Powered by PAM — Concert Discovery Engine
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
