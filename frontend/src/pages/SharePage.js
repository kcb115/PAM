import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { api } from "@/lib/api";

// ─── Music Note Word Cloud ────────────────────────────────────────────────────

function MusicNoteWordCloud({ genreMap }) {
  const canvasRef = useRef(null);
  const W = 520;
  const H = 420;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, W, H);

    const entries = Object.entries(genreMap || {})
      .sort((a, b) => b[1] - a[1])
      .slice(0, 22);
    if (!entries.length) return;

    const maxW = entries[0][1];

    // ── Draw music note mask shape ──────────────────────────────────────
    const noteCanvas = document.createElement("canvas");
    noteCanvas.width = W;
    noteCanvas.height = H;
    const nc = noteCanvas.getContext("2d");
    nc.fillStyle = "white";

    // Scale note to fit W×H canvas
    const sx = W / 380;
    const sy = H / 380;

    // Note head 1 — lower left
    nc.save(); nc.translate(102 * sx, 298 * sy); nc.rotate(-0.32);
    nc.beginPath(); nc.ellipse(0, 0, 60 * sx, 43 * sy, 0, 0, Math.PI * 2); nc.fill();
    nc.restore();

    // Note head 2 — lower right
    nc.save(); nc.translate(258 * sx, 258 * sy); nc.rotate(-0.32);
    nc.beginPath(); nc.ellipse(0, 0, 60 * sx, 43 * sy, 0, 0, Math.PI * 2); nc.fill();
    nc.restore();

    // Stem 1
    nc.fillRect(143 * sx, 88 * sy, 20 * sx, 215 * sy);
    // Stem 2
    nc.fillRect(298 * sx, 52 * sy, 20 * sx, 210 * sy);
    // Beam
    nc.beginPath();
    nc.moveTo(143 * sx, 88 * sy);
    nc.lineTo(318 * sx, 52 * sy);
    nc.lineTo(318 * sx, 84 * sy);
    nc.lineTo(143 * sx, 120 * sy);
    nc.closePath();
    nc.fill();

    const maskData = noteCanvas.getContext("2d").getImageData(0, 0, W, H).data;
    const inMask = (x, y) => {
      if (x < 0 || y < 0 || x >= W || y >= H) return false;
      return maskData[(Math.round(y) * W + Math.round(x)) * 4 + 3] > 128;
    };

    // ── Place words on the note canvas ──────────────────────────────────
    const FONT = "bold {sz}px 'JetBrains Mono', monospace";
    const COLORS = [
      "#ffffff","#ffffff","#DED5EB","#DED5EB",
      "#c4b5fd","#c4b5fd","#a78bfa","#a78bfa",
      "#8b5cf6","#7c3aed","#6d28d9","#5b21b6",
    ];
    const PAD = 3; // px padding between words

    // Occupied pixel map (coarse 2px grid for speed)
    const GRID = 2;
    const gW = Math.ceil(W / GRID);
    const gH = Math.ceil(H / GRID);
    const occupied = new Uint8Array(gW * gH);

    const markOccupied = (x1, y1, x2, y2) => {
      const gx1 = Math.max(0, Math.floor((x1 - PAD) / GRID));
      const gy1 = Math.max(0, Math.floor((y1 - PAD) / GRID));
      const gx2 = Math.min(gW - 1, Math.ceil((x2 + PAD) / GRID));
      const gy2 = Math.min(gH - 1, Math.ceil((y2 + PAD) / GRID));
      for (let gy = gy1; gy <= gy2; gy++)
        for (let gx = gx1; gx <= gx2; gx++)
          occupied[gy * gW + gx] = 1;
    };

    const isClear = (x1, y1, x2, y2) => {
      const gx1 = Math.max(0, Math.floor((x1 - PAD) / GRID));
      const gy1 = Math.max(0, Math.floor((y1 - PAD) / GRID));
      const gx2 = Math.min(gW - 1, Math.ceil((x2 + PAD) / GRID));
      const gy2 = Math.min(gH - 1, Math.ceil((y2 + PAD) / GRID));
      for (let gy = gy1; gy <= gy2; gy++)
        for (let gx = gx1; gx <= gx2; gx++)
          if (occupied[gy * gW + gx]) return false;
      return true;
    };

    const wordsFitInMask = (x1, y1, x2, y2) => {
      // Sample corners + midpoints
      const pts = [
        [x1, y1],[x2, y1],[x1, y2],[x2, y2],
        [(x1+x2)/2, y1],[(x1+x2)/2, y2],
      ];
      return pts.every(([px, py]) => inMask(px, py));
    };

    // Try placing each word with random spiral search
    entries.forEach(([word, rawWeight], i) => {
      const weight = rawWeight / maxW;
      const fontSize = Math.round(10 + weight * 16);
      const font = FONT.replace("{sz}", fontSize);
      ctx.font = font;
      const metrics = ctx.measureText(word.toUpperCase() === word ? word : word);
      const tw = metrics.width;
      const th = fontSize * 1.3;
      const color = COLORS[Math.min(i, COLORS.length - 1)];

      // Try up to 300 random positions biased towards note body
      const candidates = [];
      for (let t = 0; t < 300; t++) {
        const x = Math.random() * (W - tw);
        const y = Math.random() * (H - th);
        candidates.push([x, y]);
      }

      for (const [x, y] of candidates) {
        const x2 = x + tw;
        const y2 = y + th;
        if (wordsFitInMask(x, y, x2, y2) && isClear(x, y, x2, y2)) {
          ctx.fillStyle = color;
          ctx.font = font;
          ctx.textBaseline = "top";
          ctx.fillText(word, x, y);
          markOccupied(x, y, x2, y2);
          break;
        }
      }
    });

    // ── Apply note shape as mask ────────────────────────────────────────
    ctx.globalCompositeOperation = "destination-in";
    ctx.drawImage(noteCanvas, 0, 0);
    ctx.globalCompositeOperation = "source-over";
  }, [genreMap]);

  return (
    <canvas
      ref={canvasRef}
      width={W}
      height={H}
      style={{ maxWidth: "100%", display: "block", margin: "0 auto" }}
    />
  );
}

// ─── Share Page ───────────────────────────────────────────────────────────────

export default function SharePage() {
  const { shareId } = useParams();
  const navigate = useNavigate();
  const [share, setShare] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (shareId) {
      api
        .getShare(shareId)
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
      <div
        className="hero-gradient min-h-screen flex items-center justify-center"
        data-testid="share-error"
      >
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

  const artists = share.top_artist_names || [];

  return (
    <div className="hero-gradient min-h-screen" data-testid="share-page">
      {/* Ambient lights */}
      <div className="absolute top-0 left-[20%] w-[500px] h-[500px] bg-[#380E75]/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-[10%] w-[400px] h-[400px] bg-[#DED5EB]/4 rounded-full blur-[100px] pointer-events-none" />

      <nav className="relative z-10 flex items-center justify-between px-6 md:px-12 py-6">
        <div
          className="flex items-center gap-2 cursor-pointer"
          onClick={() => navigate("/")}
        >
          <img
            src={`${process.env.PUBLIC_URL}/PAM_logo_nav.png`}
            alt="PAM"
            className="w-10 h-10"
          />
          <span className="font-syne font-extrabold text-xl tracking-tight">
            PAM
          </span>
          <span className="text-sm text-zinc-500 ml-2">Your concert buddy</span>
        </div>
      </nav>

      <div className="relative z-10 max-w-2xl mx-auto px-6 py-8">
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

          {/* Genre Word Cloud */}
          <div className="glass-card p-6 mb-6 flex flex-col items-center">
            <p className="font-mono text-xs uppercase tracking-[0.15em] text-zinc-500 mb-6 self-start">
              Genre DNA
            </p>
            <MusicNoteWordCloud
              genreMap={share.genre_map || share.root_genre_map || {}}
            />
          </div>

          {/* Top Artists */}
          {artists.length > 0 && (
            <div className="glass-card p-6 mb-8">
              <p className="font-mono text-xs uppercase tracking-[0.15em] text-zinc-500 mb-4">
                Top Artists
              </p>
              <div className="flex flex-wrap gap-2">
                {artists.map((name) => (
                  <Badge
                    key={name}
                    variant="secondary"
                    className="text-xs font-mono border border-white/10 bg-white/5 text-zinc-300 px-3 py-1"
                  >
                    {name}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* CTA */}
          <div className="text-center">
            <Button
              onClick={() => navigate("/onboarding")}
              className="bg-[#380E75] text-[#DED5EB] font-syne font-bold uppercase tracking-wider rounded-full px-10 py-7 text-base hover:bg-[#380E75]/80 transition-all duration-200"
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
