import { useState, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Music, LogOut, RefreshCw, Share2, Heart, Search, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { TasteProfileCard } from "@/components/pam/TasteProfileCard";
import { LocationSearch } from "@/components/pam/LocationSearch";
import { ConcertList } from "@/components/pam/ConcertList";
import { FavoritesList } from "@/components/pam/FavoritesList";
import { LoadingState } from "@/components/pam/LoadingState";
import { motion } from "framer-motion";

export default function DashboardPage({ user, onSaveUser, onLogout }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [tasteProfile, setTasteProfile] = useState(null);
  const [concerts, setConcerts] = useState([]);
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState("");
  const [message, setMessage] = useState("");
  const [totalScanned, setTotalScanned] = useState(0);
  const [shareUrl, setShareUrl] = useState("");
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState("discover");
  const [sessionId, setSessionId] = useState(() =>
    localStorage.getItem("pam_session_id") || ""
  );

  // Handle OAuth callback params
  useEffect(() => {
    const sid = searchParams.get("session_id");
    const uid = searchParams.get("user_id");

    if (sid) {
      setSessionId(sid);
      localStorage.setItem("pam_session_id", sid);
    }

    if (uid && !user) {
      api.getUser(uid).then((res) => {
        onSaveUser(res.data);
      }).catch(() => {});
    }
  }, [searchParams, user, onSaveUser]);

  // Load existing taste profile & favorites
  useEffect(() => {
    if (user?.id) {
      api.getTasteProfile(user.id).then((res) => {
        setTasteProfile(res.data);
      }).catch(() => {});

      api.getFavorites(user.id).then((res) => {
        setFavorites(res.data || []);
      }).catch(() => {});
    }
  }, [user?.id]);

  const buildTasteProfile = useCallback(async () => {
    if (!sessionId || !user?.id) {
      toast.error("Spotify session not found. Please reconnect.");
      return;
    }
    setLoading("taste");
    try {
      const res = await api.buildTasteProfile(sessionId, user.id);
      setTasteProfile(res.data);
      toast.success("Your taste fingerprint is ready!");
    } catch (err) {
      console.error(err);
      const msg = err.response?.data?.detail || "Failed to build taste profile";
      toast.error(msg);
    } finally {
      setLoading("");
    }
  }, [sessionId, user?.id]);

  // Auto-build taste profile on first visit after OAuth
  useEffect(() => {
    if (sessionId && user?.id && !tasteProfile) {
      buildTasteProfile();
    }
  }, [sessionId, user?.id, tasteProfile, buildTasteProfile]);

  const handleDiscover = async (city, radius, dateFrom, dateTo) => {
    if (!user?.id) return;
    if (!tasteProfile) {
      toast.error("Build your taste profile first");
      return;
    }

    setLoading("discover");
    setConcerts([]);
    setMessage("");
    setTotalScanned(0);

    try {
      const res = await api.discoverConcerts({
        user_id: user.id,
        city,
        radius,
        date_from: dateFrom,
        date_to: dateTo,
      });

      setConcerts(res.data.concerts || []);
      setMessage(res.data.message || "");
      setTotalScanned(res.data.total_events_scanned || 0);

      if (res.data.concerts?.length > 0) {
        toast.success(`Found ${res.data.concerts.length} matching artists!`);
      } else if (res.data.message) {
        toast.info(res.data.message);
      }
    } catch (err) {
      console.error(err);
      const msg = err.response?.data?.detail || "Discovery failed";
      toast.error(msg);
    } finally {
      setLoading("");
    }
  };

  const handleFavorite = async (concert) => {
    if (!user?.id) return;
    const isSaved = favorites.some((f) => f.concert.event_id === concert.event_id);

    if (isSaved) {
      const fav = favorites.find((f) => f.concert.event_id === concert.event_id);
      if (fav) {
        try {
          await api.removeFavorite(fav.id);
          setFavorites((prev) => prev.filter((f) => f.id !== fav.id));
          toast.success("Removed from favorites");
        } catch (err) {
          toast.error("Failed to remove");
        }
      }
    } else {
      try {
        const res = await api.addFavorite({ user_id: user.id, concert });
        setFavorites((prev) => [...prev, res.data]);
        toast.success("Saved to favorites!");
      } catch (err) {
        toast.error("Failed to save");
      }
    }
  };

  const handleRemoveFavorite = async (favoriteId) => {
    try {
      await api.removeFavorite(favoriteId);
      setFavorites((prev) => prev.filter((f) => f.id !== favoriteId));
      toast.success("Removed from favorites");
    } catch (err) {
      toast.error("Failed to remove");
    }
  };

  const handleShare = async () => {
    if (!user?.id) return;
    try {
      const res = await api.createShare(user.id);
      const url = `${window.location.origin}/share/${res.data.share_id}`;
      setShareUrl(url);
      await navigator.clipboard.writeText(url);
      setCopied(true);
      toast.success("Share link copied to clipboard!");
      setTimeout(() => setCopied(false), 3000);
    } catch (err) {
      toast.error("Failed to generate share link");
    }
  };

  const handleLogout = () => {
    onLogout();
    navigate("/");
  };

  const favoriteEventIds = new Set(favorites.map((f) => f.concert.event_id));

  // If no user, redirect to onboarding
  if (!user && !searchParams.get("user_id")) {
    return (
      <div className="hero-gradient min-h-screen flex items-center justify-center" data-testid="dashboard-no-user">
        <div className="text-center">
          <p className="text-zinc-400 mb-4">No profile found.</p>
          <Button
            onClick={() => navigate("/onboarding")}
            className="bg-[#380E75] text-[#DED5EB] font-syne font-bold rounded-full px-8 py-6"
            data-testid="go-onboarding-btn"
          >
            Get Started
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="hero-gradient min-h-screen" data-testid="dashboard-page">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-black/60 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 md:px-8 flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#380E75] flex items-center justify-center">
              <Music className="w-4 h-4 text-[#DED5EB]" />
            </div>
            <span className="font-syne font-extrabold text-lg tracking-tight">PAM</span>
          </div>

          <div className="flex items-center gap-3">
            {tasteProfile && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleShare}
                className="text-zinc-500 hover:text-amber-400 text-xs font-mono"
                data-testid="share-btn"
              >
                {copied ? <Check className="w-4 h-4 mr-1" /> : <Share2 className="w-4 h-4 mr-1" />}
                {copied ? "Copied!" : "Share"}
              </Button>
            )}
            {user && (
              <span className="text-xs font-mono text-zinc-500 hidden sm:block" data-testid="user-greeting">
                {user.name}
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="text-zinc-500 hover:text-white"
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 md:px-8 py-8 md:py-12">
        {/* Loading overlay */}
        {loading && <LoadingState type={loading} />}

        {/* Taste Profile */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-amber-500/80 mb-1">
                Your Sound
              </p>
              <h2 className="font-syne text-2xl md:text-3xl font-bold tracking-tight">
                Taste Fingerprint
              </h2>
            </div>
            <div className="flex items-center gap-2">
              {tasteProfile && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={buildTasteProfile}
                  disabled={!!loading}
                  className="text-zinc-500 hover:text-white"
                  data-testid="refresh-profile-btn"
                >
                  <RefreshCw className="w-4 h-4 mr-1" />
                  Refresh
                </Button>
              )}
            </div>
          </div>

          {tasteProfile ? (
            <TasteProfileCard profile={tasteProfile} />
          ) : !loading ? (
            <div className="glass-card p-8 text-center" data-testid="no-profile-state">
              <p className="text-zinc-400 mb-4">
                {sessionId
                  ? "Building your taste fingerprint..."
                  : "Connect Spotify to build your taste fingerprint."}
              </p>
              {!sessionId && (
                <Button
                  onClick={async () => {
                    if (!user?.id) return;
                    const res = await api.spotifyLogin(user.id);
                    const authUrl = res.data.auth_url;
                    try {
                      if (window.top !== window.self) {
                        window.top.location.href = authUrl;
                      } else {
                        window.location.href = authUrl;
                      }
                    } catch {
                      window.open(authUrl, '_blank');
                    }
                  }}
                  className="spotify-btn px-8 py-6"
                  data-testid="reconnect-spotify-btn"
                >
                  Connect Spotify
                </Button>
              )}
            </div>
          ) : null}
        </motion.div>

        {/* Tabs: Discover / Favorites */}
        {tasteProfile && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-12"
          >
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="bg-secondary/50 border border-white/5 rounded-full p-1 mb-8">
                <TabsTrigger
                  value="discover"
                  className="rounded-full font-syne font-bold text-sm data-[state=active]:bg-amber-500 data-[state=active]:text-black px-6"
                  data-testid="discover-tab"
                >
                  <Search className="w-4 h-4 mr-2" />
                  Discover
                </TabsTrigger>
                <TabsTrigger
                  value="favorites"
                  className="rounded-full font-syne font-bold text-sm data-[state=active]:bg-amber-500 data-[state=active]:text-black px-6"
                  data-testid="favorites-tab"
                >
                  <Heart className="w-4 h-4 mr-2" />
                  Saved ({favorites.length})
                </TabsTrigger>
              </TabsList>

              <TabsContent value="discover">
                <LocationSearch
                  onSearch={handleDiscover}
                  loading={loading === "discover"}
                  defaultCity={user?.city || ""}
                  defaultRadius={user?.radius || 25}
                />

                {(concerts.length > 0 || message) && (
                  <div className="mt-12">
                    <ConcertList
                      concerts={concerts}
                      message={message}
                      totalScanned={totalScanned}
                      onFavorite={handleFavorite}
                      favoriteIds={favoriteEventIds}
                    />
                  </div>
                )}
              </TabsContent>

              <TabsContent value="favorites">
                <div className="mb-6">
                  <p className="font-mono text-xs uppercase tracking-[0.2em] text-amber-500/80 mb-1">
                    Your Collection
                  </p>
                  <h2 className="font-syne text-2xl md:text-3xl font-bold tracking-tight">
                    Saved Concerts
                  </h2>
                </div>
                <FavoritesList
                  favorites={favorites}
                  onRemove={handleRemoveFavorite}
                />
              </TabsContent>
            </Tabs>
          </motion.div>
        )}

        {/* Share URL display */}
        {shareUrl && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8 glass-card p-4 flex items-center gap-3"
            data-testid="share-url-display"
          >
            <Share2 className="w-4 h-4 text-amber-500 shrink-0" />
            <code className="flex-1 font-mono text-xs text-zinc-400 truncate">
              {shareUrl}
            </code>
            <Button
              variant="ghost"
              size="sm"
              onClick={async () => {
                await navigator.clipboard.writeText(shareUrl);
                setCopied(true);
                toast.success("Copied!");
                setTimeout(() => setCopied(false), 3000);
              }}
              className="text-amber-400 shrink-0"
              data-testid="copy-share-url-btn"
            >
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            </Button>
          </motion.div>
        )}
      </div>
    </div>
  );
}
