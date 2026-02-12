import { ConcertCard } from "./ConcertCard";
import { Heart, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export const FavoritesList = ({ favorites, onRemove }) => {
  if (!favorites || favorites.length === 0) {
    return (
      <div className="glass-card p-8 text-center" data-testid="empty-favorites">
        <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center mx-auto mb-4">
          <Heart className="w-6 h-6 text-zinc-500" />
        </div>
        <p className="text-zinc-400 mb-1">No saved concerts yet</p>
        <p className="text-xs font-mono text-zinc-600">
          Discover concerts and save your favorites here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="favorites-list">
      {favorites.map((fav, index) => (
        <div key={fav.id} className="relative">
          <ConcertCard concert={fav.concert} rank={index + 1} />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onRemove(fav.id)}
            className="absolute top-4 right-4 text-red-400/60 hover:text-red-400 hover:bg-red-500/10"
            data-testid={`remove-favorite-${index + 1}`}
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      ))}
    </div>
  );
};
