import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { RefreshCw } from "lucide-react";

export const TasteProfileCard = ({ profile, onRegenerateNarrative }) => {
  const { genre_map, taste_narrative } = profile;
  const [regenerating, setRegenerating] = useState(false);

  const allGenres = Object.entries(genre_map || {})
    .sort((a, b) => b[1] - a[1]);

  // Top 8 as bars, rest as cloud
  const topGenres = allGenres.slice(0, 8);
  const remainingGenres = allGenres.slice(8, 20);

  const handleRegenerate = async () => {
    if (!onRegenerateNarrative || regenerating) return;
    setRegenerating(true);
    try {
      await onRegenerateNarrative();
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div data-testid="taste-profile-card">
      {/* AI Narrative (full width) */}
      {taste_narrative && (
        <div className="glass-card p-6 mb-6" data-testid="taste-narrative">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <p className="font-mono text-xs uppercase tracking-[0.15em] text-zinc-500 mb-3">
                Your Listening Identity
              </p>
              <p className="font-jakarta text-sm md:text-base text-zinc-300 leading-relaxed">
                {taste_narrative}
              </p>
            </div>
            {onRegenerateNarrative && (
              <button
                onClick={handleRegenerate}
                disabled={regenerating}
                className="shrink-0 mt-6 p-2 rounded-lg text-zinc-600 hover:text-[#DED5EB] hover:bg-white/5 transition-colors disabled:opacity-40"
                title="Regenerate description"
                data-testid="regenerate-narrative-btn"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${regenerating ? "animate-spin" : ""}`} />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Genre bars + cloud (two-column grid) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Genres (weighted bars) */}
        <div className="glass-card p-6">
          <p className="font-mono text-xs uppercase tracking-[0.15em] text-zinc-500 mb-4">
            Your Top Genres
          </p>
          <div className="space-y-3" data-testid="root-genres-list">
            {topGenres.map(([genre, weight]) => (
              <div key={genre} className="flex items-center gap-3">
                <span className="font-jakarta text-sm text-zinc-300 w-32 truncate capitalize">
                  {genre}
                </span>
                <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full match-bar-fill"
                    style={{
                      "--score-width": `${Math.round(weight * 100)}%`,
                      width: `${Math.round(weight * 100)}%`,
                      background: weight > 0.6
                        ? "#DED5EB"
                        : weight > 0.3
                        ? "#380E75"
                        : "#3f3f46",
                    }}
                  />
                </div>
                <span className="font-mono text-xs text-zinc-600 w-10 text-right">
                  {Math.round(weight * 100)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Genre Cloud */}
        <div className="glass-card p-6">
          <p className="font-mono text-xs uppercase tracking-[0.15em] text-zinc-500 mb-4">
            Genre Cloud
          </p>
          <div className="flex flex-wrap gap-2" data-testid="genre-cloud">
            {remainingGenres.map(([genre, weight]) => (
              <Badge
                key={genre}
                variant="secondary"
                className={`text-xs font-mono border transition-colors duration-200 cursor-default ${
                  weight > 0.5
                    ? "border-[#DED5EB]/30 bg-[#380E75]/20 text-[#DED5EB]"
                    : weight > 0.25
                    ? "border-[#380E75]/30 bg-[#380E75]/10 text-[#DED5EB]/70"
                    : "border-white/10 bg-white/5 text-zinc-400"
                }`}
              >
                {genre}
              </Badge>
            ))}
          </div>
          <div className="mt-6 pt-4 border-t border-white/5">
            <p className="font-mono text-xs text-zinc-600">
              Based on {profile.top_artist_names?.length || 0} of your top artists
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
