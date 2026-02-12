import { useState, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Music, LogOut, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { TasteProfileCard } from "@/components/pam/TasteProfileCard";
import { LocationSearch } from "@/components/pam/LocationSearch";
import { ConcertList } from "@/components/pam/ConcertList";
import { LoadingState } from "@/components/pam/LoadingState";
import { motion } from "framer-motion";

export default function DashboardPage({ user, onSaveUser, onLogout }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [tasteProfile, setTasteProfile] = useState(null);
  const [concerts, setConcerts] = useState([]);
  const [loading, setLoading] = useState("");
  const [message, setMessage] = useState("");
  const [totalScanned, setTotalScanned] = useState(0);
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
      // Fetch user from backend
      api.getUser(uid).then((res) => {
        onSaveUser(res.data);
      }).catch(() => {});
    }
  }, [searchParams, user, onSaveUser]);

  // Try loading existing taste profile
  useEffect(() => {
    if (user?.id) {
      api.getTasteProfile(user.id).then((res) => {
        setTasteProfile(res.data);
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

  const handleDiscover = async (city, radius) => {
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
      });

      setConcerts(res.data.concerts || []);
      setMessage(res.data.message || "");
      setTotalScanned(res.data.total_events_scanned || 0);

      if (res.data.concerts?.length > 0) {
        toast.success(`Found ${res.data.concerts.length} matching concerts!`);
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

  const handleLogout = () => {
    onLogout();
    navigate("/");
  };

  // If no user, redirect to onboarding
  if (!user && !searchParams.get("user_id")) {
    return (
      <div className="hero-gradient min-h-screen flex items-center justify-center" data-testid="dashboard-no-user">
        <div className="text-center">
          <p className="text-zinc-400 mb-4">No profile found.</p>
          <Button
            onClick={() => navigate("/onboarding")}
            className="bg-amber-500 text-black font-syne font-bold rounded-full px-8 py-6"
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
            <div className="w-8 h-8 rounded-lg bg-amber-500 flex items-center justify-center">
              <Music className="w-4 h-4 text-black" />
            </div>
            <span className="font-syne font-extrabold text-lg tracking-tight">PAM</span>
          </div>

          <div className="flex items-center gap-4">
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
                    window.location.href = res.data.auth_url;
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

        {/* Location Search */}
        {tasteProfile && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-12"
          >
            <LocationSearch
              onSearch={handleDiscover}
              loading={loading === "discover"}
              defaultCity={user?.city || ""}
              defaultRadius={user?.radius || 25}
            />
          </motion.div>
        )}

        {/* Concert Results */}
        {(concerts.length > 0 || message) && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="mt-12"
          >
            <ConcertList
              concerts={concerts}
              message={message}
              totalScanned={totalScanned}
            />
          </motion.div>
        )}
      </div>
    </div>
  );
}
