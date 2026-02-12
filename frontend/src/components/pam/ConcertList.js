import { ConcertCard } from "./ConcertCard";
import { MapPin, AlertCircle } from "lucide-react";

export const ConcertList = ({ concerts, message, totalScanned, onFavorite, favoriteIds }) => {
  return (
    <div data-testid="concert-list">
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-amber-500/80 mb-1">
            Results
          </p>
          <h2 className="font-syne text-2xl md:text-3xl font-bold tracking-tight">
            Your Matches
          </h2>
        </div>
        {totalScanned > 0 && (
          <span className="font-mono text-xs text-zinc-600" data-testid="events-scanned-count">
            {totalScanned} artists discovered
          </span>
        )}
      </div>

      {concerts.length > 0 ? (
        <div className="space-y-4">
          {concerts.map((concert, index) => (
            <ConcertCard
              key={concert.event_id || index}
              concert={concert}
              rank={index + 1}
              onFavorite={onFavorite}
              isFavorited={favoriteIds?.has(concert.event_id)}
            />
          ))}
        </div>
      ) : message ? (
        <div
          className="glass-card p-8 text-center"
          data-testid="empty-concerts-state"
        >
          <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-6 h-6 text-zinc-500" />
          </div>
          <p className="text-zinc-400 mb-2">{message}</p>
          <p className="text-xs font-mono text-zinc-600">
            Try a larger radius or a different city.
          </p>
        </div>
      ) : null}
    </div>
  );
};
