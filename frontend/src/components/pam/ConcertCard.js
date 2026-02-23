import { useState } from "react";
import {
  MapPin,
  Calendar,
  Ticket,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Info,
  Heart,
  Music2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export const ConcertCard = ({ concert, rank, onFavorite, isFavorited }) => {
  const [expanded, setExpanded] = useState(false);

  const {
    artist_name,
    genre_description,
    match_score,
    match_explanation,
    venue_name,
    venue_city,
    date,
    time,
    ticket_url,
    event_url,
    spotify_artist_url,
    spotify_popularity,
    featured_track,
  } = concert;

  // Format date
  const formatDate = (dateStr) => {
    if (!dateStr) return "TBA";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-US", {
        weekday: "short",
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  // Score color
  const getScoreColor = (score) => {
    if (score >= 70) return "text-[#DED5EB]";
    if (score >= 45) return "text-[#DED5EB]/70";
    return "text-zinc-400";
  };

  const getBarColor = (score) => {
    if (score >= 70) return "#DED5EB";
    if (score >= 45) return "#380E75";
    return "#52525b";
  };

  // Indie badge
  const isIndie = spotify_popularity !== null && spotify_popularity < 40;

  return (
    <div
      className="concert-card p-5 md:p-6"
      data-testid={`concert-card-${rank}`}
    >
      <div className="flex flex-col md:flex-row md:items-start gap-4">
        {/* Rank indicator */}
        <div className="hidden md:flex flex-col items-center justify-center w-10">
          <span className="font-mono text-xs text-zinc-600">#{rank}</span>
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {/* Header row */}
          <div className="flex items-start justify-between gap-3 mb-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h3
                  className="font-syne font-bold text-lg text-white truncate"
                  data-testid={`artist-name-${rank}`}
                >
                  {artist_name}
                </h3>
                {isIndie && (
                  <Badge
                    variant="outline"
                    className="text-[10px] font-mono border-[#380E75]/50 text-[#DED5EB] shrink-0"
                  >
                    INDIE
                  </Badge>
                )}
              </div>
              <p className="text-xs text-zinc-500 font-mono truncate">
                {genre_description}
              </p>
            </div>

            {/* Match score */}
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div
                    className="flex flex-col items-end shrink-0 cursor-help"
                    data-testid={`match-score-${rank}`}
                  >
                    <span className={`font-mono text-2xl font-bold ${getScoreColor(match_score)}`}>
                      {Math.round(match_score)}
                    </span>
                    <span className="font-mono text-[10px] text-zinc-600 uppercase tracking-wider">
                      match
                    </span>
                  </div>
                </TooltipTrigger>
                <TooltipContent
                  side="left"
                  className="bg-zinc-900 border-white/10 text-xs max-w-xs"
                >
                  <p>Genre match score based on your listening taste</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          {/* Score bar */}
          <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden mb-4">
            <div
              className="h-full rounded-full match-bar-fill"
              style={{
                "--score-width": `${Math.min(match_score, 100)}%`,
                width: `${Math.min(match_score, 100)}%`,
                background: getBarColor(match_score),
              }}
            />
          </div>

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-zinc-400">
            <span className="flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-[#380E75]" />
              {venue_name}
              {venue_city && `, ${venue_city}`}
            </span>
            <span className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-[#DED5EB]" />
              {formatDate(date)}
              {time && ` at ${time}`}
            </span>
            {spotify_popularity !== null && (
              <span className="font-mono text-zinc-600">
                pop: {spotify_popularity}
              </span>
            )}
          </div>

          {/* Actions row */}
          <div className="flex items-center gap-3 mt-4">
            {onFavorite && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onFavorite(concert)}
                className={`text-xs font-mono rounded-full ${
                  isFavorited
                    ? "text-[#DED5EB] bg-[#380E75]/20"
                    : "text-zinc-500 hover:text-[#DED5EB] hover:bg-[#380E75]/10"
                }`}
                data-testid={`favorite-btn-${rank}`}
              >
                <Heart className={`w-3.5 h-3.5 mr-1 ${isFavorited ? "fill-current" : ""}`} />
                {isFavorited ? "Saved" : "Save"}
              </Button>
            )}

            {(ticket_url || event_url) && (
              <a
                href={ticket_url || event_url}
                target="_blank"
                rel="noopener noreferrer"
                data-testid={`ticket-link-${rank}`}
              >
                <Button
                  size="sm"
                  className="bg-[#380E75]/20 text-[#DED5EB] hover:bg-[#380E75]/30 border border-[#380E75]/30 rounded-full text-xs font-mono"
                >
                  <Ticket className="w-3.5 h-3.5 mr-1.5" />
                  Tickets
                  <ExternalLink className="w-3 h-3 ml-1" />
                </Button>
              </a>
            )}

            {spotify_artist_url && (
              <a
                href={spotify_artist_url}
                target="_blank"
                rel="noopener noreferrer"
                data-testid={`spotify-link-${rank}`}
              >
                <Button
                  size="sm"
                  className="rounded-full text-xs font-mono"
                  style={{
                    backgroundColor: "rgba(29,185,84,0.15)",
                    color: "#1DB954",
                    border: "1px solid rgba(29,185,84,0.3)",
                  }}
                  onMouseEnter={e => e.currentTarget.style.backgroundColor = "rgba(29,185,84,0.25)"}
                  onMouseLeave={e => e.currentTarget.style.backgroundColor = "rgba(29,185,84,0.15)"}
                >
                  <svg className="w-3.5 h-3.5 mr-1.5" viewBox="0 0 24 24" fill="#1DB954" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                  </svg>
                  Listen
                  <ExternalLink className="w-3 h-3 ml-1" />
                </Button>
              </a>
            )}

            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpanded(!expanded)}
              className="text-zinc-500 hover:text-white text-xs font-mono"
              data-testid={`why-match-btn-${rank}`}
            >
              <Info className="w-3.5 h-3.5 mr-1" />
              Why this match?
              {expanded ? (
                <ChevronUp className="w-3.5 h-3.5 ml-1" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5 ml-1" />
              )}
            </Button>
          </div>

          {/* Featured track */}
          {featured_track && (
            <div className="mt-3 flex items-center gap-2 text-xs text-zinc-500">
              <Music2 className="w-3 h-3 text-[#DED5EB]/60" />
              <span className="font-mono">Featured: {featured_track}</span>
            </div>
          )}

          {/* Expandable explanation */}
          {expanded && (
            <div
              className="mt-3 p-4 rounded-xl bg-white/[0.02] border border-white/5"
              data-testid={`match-explanation-${rank}`}
            >
              <p className="text-sm text-zinc-300 leading-relaxed">
                {match_explanation}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
