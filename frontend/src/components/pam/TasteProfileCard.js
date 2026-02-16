import { Badge } from "@/components/ui/badge";

export const TasteProfileCard = ({ profile }) => {
  const { genre_map, root_genre_map } = profile;

  // Top genres for display
  const topGenres = Object.entries(genre_map || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 12);

  const topRootGenres = Object.entries(root_genre_map || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" data-testid="taste-profile-card">
      {/* Root Genres (weighted) */}
      <div className="glass-card p-6">
        <p className="font-mono text-xs uppercase tracking-[0.15em] text-zinc-500 mb-4">
          Your Top Genres
        </p>
        <div className="space-y-3" data-testid="root-genres-list">
          {topRootGenres.map(([genre, weight]) => (
            <div key={genre} className="flex items-center gap-3">
              <span className="font-jakarta text-sm text-zinc-300 w-24 truncate capitalize">
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

      {/* Detailed Genre Tags */}
      <div className="glass-card p-6">
        <p className="font-mono text-xs uppercase tracking-[0.15em] text-zinc-500 mb-4">
          Genre Cloud
        </p>
        <div className="flex flex-wrap gap-2" data-testid="genre-cloud">
          {topGenres.map(([genre, weight]) => (
            <Badge
              key={genre}
              variant="secondary"
              className={`text-xs font-mono border transition-colors duration-200 cursor-default ${
                weight > 0.7
                  ? "border-[#DED5EB]/30 bg-[#380E75]/20 text-[#DED5EB]"
                  : weight > 0.4
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
  );
};
