import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { api } from "@/lib/api";

// ─── Music Note Word Cloud ────────────────────────────────────────────────────

function MusicNoteWordCloud({ genreMap, fallbackGenres }) {
  const [words, setWords] = useState([]);
  const SIZE = 380;

  useEffect(() => {
    // Build genre list from map (weighted) or fallback array (equal weight)
    let entries = [];
    if (genreMap && Object.keys(genreMap).length > 0) {
      entries = Object.entries(genreMap)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 22);
    } else if (fallbackGenres?.length) {
      entries = fallbackGenres.map((g, i) => [g, 1 - i * 0.05]);
    }
    if (!entries.length) return;

    // Draw a bold double eighth note on an offscreen canvas
    const canvas = document.createElement("canvas");
    canvas.width = SIZE;
    canvas.height = SIZE;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "white";

    // Note head 1 — lower left
    ctx.save();
    ctx.translate(102, 298);
    ctx.rotate(-0.32);
    ctx.beginPath();
    ctx.ellipse(0, 0, 60, 43, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Note head 2 — lower right
    ctx.save();
    ctx.translate(258, 258);
    ctx.rotate(-0.32);
    ctx.beginPath();
    ctx.ellipse(0, 0, 60, 43, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Stem 1 — left
    ctx.fillRect(143, 88, 20, 215);

    // Stem 2 — right
    ctx.fillRect(298, 52, 20, 210);

    // Top beam
    ctx.beginPath();
    ctx.moveTo(143, 88);
    ctx.lineTo(318, 52);
    ctx.lineTo(318, 84);
    ctx.lineTo(143, 120);
    ctx.closePath();
    ctx.fill();

    // Scan valid cells (CELL x CELL pixel blocks inside the note)
    const CELL = 10;
    const cols = Math.ceil(SIZE / CELL);
    const rows = Math.ceil(SIZE / CELL);
    const imgData = ctx.getImageData(0, 0, SIZE, SIZE).data;

    const isValid = (col, row) => {
      const px = col * CELL + Math.floor(CELL / 2);
      const py = row * CELL + Math.floor(CELL / 2);
      if (px >= SIZE || py >= SIZE) return false;
      return imgData[(py * SIZE + px) * 4 + 3] > 128;
    };

    const validSet = new Set();
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (isValid(c, r)) validSet.add(`${c},${r}`);
      }
    }

    // Shuffle valid cells for random placement
    const validList = Array.from(validSet);
    for (let i = validList.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [validList[i], validList[j]] = [validList[j], validList[i]];
    }

    const maxWeight = entries[0]?.[1] || 1;
    const colors = [
      "#ffffff", "#ffffff", "#DED5EB", "#DED5EB",
      "#c4b5fd", "#c4b5fd", "#a78bfa", "#a78bfa",
      "#8b5cf6", "#7c3aed", "#6d28d9", "#5b21b6",
    ];

    const occupied = new Set();
    const placed = [];

    entries.forEach(([genre, weight], i) => {
      const normalized = weight / maxWeight;
      // Font size range: 11px (min) to 28px (max)
      const fontSize = Math.round(11 + normalized * 17);
      // Approximate word bounding box in cells
      const charW = fontSize * 0.58;
      const wordCols = Math.ceil((genre.length * charW) / CELL) + 1;
      const wordRows = Math.ceil((fontSize * 1.4) / CELL) + 1;
      const color = colors[Math.min(i, colors.length - 1)];

      for (const cellKey of validList) {
        const [c, r] = cellKey.split(",").map(Number);
        // Check all cells the word would occupy
        let fits = true;
        const needed = [];
        for (let dc = 0; dc < wordCols && fits; dc++) {
          for (let dr = 0; dr < wordRows && fits; dr++) {
            const k = `${c + dc},${r + dr}`;
            if (!validSet.has(k) || occupied.has(k)) {
              fits = false;
            } else {
              needed.push(k);
            }
          }
        }
        if (fits) {
          needed.forEach((k) => occupied.add(k));
          placed.push({
            word: genre,
            x: c * CELL,
            y: r * CELL,
            fontSize,
            color,
          });
          break;
        }
      }
    });

    setWords(placed);
  }, [genreMap, fallbackGenres]);

  return (
    <div
      style={{
        position: "relative",
        width: SIZE,
        height: SIZE,
        margin: "0 auto",
      }}
    >
      {words.map(({ word, x, y, fontSize, color }) => (
        <span
          key={word}
          style={{
            position: "absolute",
            left: x,
            top: y,
            fontSize,
            color,
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: "bold",
            textTransform: "capitalize",
            whiteSpace: "nowrap",
            lineHeight: 1.4,
            userSelect: "none",
            textShadow: "0 1px 6px rgba(0,0,0,0.6)",
          }}
        >
          {word}
        </span>
      ))}
    </div>
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
              genreMap={share.root_genre_map}
              fallbackGenres={share.top_genres}
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
