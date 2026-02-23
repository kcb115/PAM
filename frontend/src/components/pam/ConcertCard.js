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
                  <svg className="w-3.5 h-3.5 mr-1.5" viewBox="0 0 496 512" fill="#1DB954" xmlns="http://www.w3.org/2000/svg">
                    <path d="M248 8C111.1 8 0 119.1 0 256s111.1 248 248 248 248-111.1 248-248S384.9 8 248 8zm100.7 357.2c-4.9 8-15.3 10.5-23.2 5.7-63.5-38.8-143.3-47.6-237.4-26.1-9.1 2.1-18.2-3.6-20.3-12.7-2.1-9.1 3.6-18.2 12.7-20.3 102.8-23.5 191.1-13.4 262.3 30.2 7.9 4.9 10.4 15.3 5.9 23.2zm26.9-59.7c-6.1 9.9-19.1 13-29 6.9-72.6-44.6-183.2-57.5-269-31.5-10.5 3.2-21.5-2.8-24.7-13.2-3.2-10.5 2.8-21.5 13.2-24.7 98.3-29.8 220.4-15.3 303.5 35.9 9.9 6.1 13 19.1 6 29zm2.3-62.3c-87.1-51.7-230.8-56.5-314-31.2-12.6 3.8-26-3.3-29.8-15.9-3.8-12.6 3.3-26 15.9-29.8 95.5-29 254.1-23.4 354.4 36.1 11.3 6.7 15.1 21.3 8.4 32.6-6.7 11.3-21.3 15.1-32.6 8.4l-2.3-0.2z"/>
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
