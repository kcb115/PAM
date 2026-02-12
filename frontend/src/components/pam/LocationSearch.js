import { useState } from "react";
import { MapPin, Search, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const RADIUS_OPTIONS = [10, 25, 50, 75, 100, 150];

export const LocationSearch = ({ onSearch, loading, defaultCity, defaultRadius }) => {
  const [city, setCity] = useState(defaultCity || "");
  const [radius, setRadius] = useState(String(defaultRadius || 25));

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!city.trim()) return;
    onSearch(city.trim(), parseInt(radius));
  };

  return (
    <div data-testid="location-search">
      <div className="mb-6">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-teal-500/80 mb-1">
          Discover
        </p>
        <h2 className="font-syne text-2xl md:text-3xl font-bold tracking-tight">
          Find Local Shows
        </h2>
      </div>

      <form onSubmit={handleSubmit} className="glass-card p-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <Label className="text-xs font-mono uppercase tracking-wider text-zinc-500 mb-2 flex items-center gap-1.5">
              <MapPin className="w-3 h-3" /> City
            </Label>
            <Input
              placeholder="e.g. Austin, TX"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="bg-secondary/50 border-white/10 h-12 px-4 font-jakarta text-sm placeholder:text-zinc-600 rounded-lg"
              data-testid="city-input"
            />
          </div>

          <div className="w-full sm:w-40">
            <Label className="text-xs font-mono uppercase tracking-wider text-zinc-500 mb-2 flex items-center gap-1.5">
              Radius
            </Label>
            <Select value={radius} onValueChange={setRadius}>
              <SelectTrigger
                className="bg-secondary/50 border-white/10 h-12 font-mono text-sm rounded-lg"
                data-testid="radius-select"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-zinc-900 border-white/10">
                {RADIUS_OPTIONS.map((r) => (
                  <SelectItem
                    key={r}
                    value={String(r)}
                    className="font-mono text-sm"
                  >
                    {r} miles
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-end">
            <Button
              type="submit"
              disabled={loading || !city.trim()}
              className="w-full sm:w-auto bg-teal-500 text-black font-syne font-bold uppercase tracking-wider rounded-full h-12 px-8 hover:bg-teal-400 transition-colors duration-200 disabled:opacity-50"
              data-testid="discover-btn"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                  Searching...
                </span>
              ) : (
                <>
                  <Search className="w-4 h-4 mr-2" />
                  Discover
                </>
              )}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
};
