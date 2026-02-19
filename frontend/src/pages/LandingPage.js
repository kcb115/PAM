import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Radio, MapPin, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

const TERMS = `Terms & Conditions
Last updated: February 2026

1. Acceptance
By creating a PAM account you agree to these terms. If you do not agree, do not use the service.

2. What PAM Does
PAM connects to your Spotify account to build a taste profile and uses that profile to suggest local concerts that match your music preferences. If you provide a phone number, PAM may send you SMS concert recommendations.

3. SMS Notifications
By providing your phone number you consent to receiving automated SMS messages from PAM containing concert suggestions. Message frequency is based on your stated concert preferences. Message and data rates may apply. You can opt out at any time by contacting us or removing your phone number from your profile.

4. Spotify Data
PAM accesses your Spotify listening data (top artists and genres) solely to generate concert recommendations. We do not share your Spotify data with third parties.

5. Ticket Purchases
PAM provides links to third-party ticketing platforms. We are not responsible for any transactions made on those platforms.

6. Limitation of Liability
PAM is provided as-is. We make no guarantees about the accuracy or availability of concert information. We are not liable for any losses arising from use of the service.

7. Changes
We may update these terms at any time. Continued use of PAM after changes constitutes acceptance.

8. Contact
For questions email us at hello@pamapp.com`;

const PRIVACY = `Privacy Policy
Last updated: February 2026

1. Information We Collect
- Name and email address (required to create an account)
- Phone number (optional, for SMS concert alerts)
- Spotify listening data: top artists and genre tags
- Location/city you enter when searching for concerts

2. How We Use Your Information
- To build your music taste profile and match it against local concerts
- To send you SMS concert recommendations if you opt in
- To save your favorited concerts
- To generate a shareable taste profile if you choose to use that feature

We do not sell your personal information to third parties.

3. Third-Party Services
PAM integrates with the following services:
- Spotify: to retrieve your listening data. Spotify's privacy policy applies to your Spotify account.
- Twilio: to send SMS messages if you provide a phone number.
- Jambase / Ticketmaster: to source concert event data.

4. Data Storage
Your data is stored securely in a hosted database. We retain your data for as long as your account is active.

5. Your Rights
You may request deletion of your account and associated data at any time by contacting us at hello@pamapp.com.

6. SMS Opt-Out
If you provided a phone number and wish to stop receiving SMS messages, contact us at hello@pamapp.com and we will remove your number.

7. Changes
We may update this policy periodically. We will notify you of significant changes via email.

8. Contact
hello@pamapp.com`;

function LegalModal({ title, content, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-zinc-900 border border-white/10 rounded-2xl w-full max-w-lg max-h-[80vh] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <h3 className="font-syne font-bold text-lg text-white">{title}</h3>
          <button onClick={onClose} className="text-zinc-400 hover:text-white text-xl leading-none">&times;</button>
        </div>
        <div className="overflow-y-auto px-6 py-4 text-zinc-400 text-xs font-jakarta leading-relaxed whitespace-pre-wrap">
          {content}
        </div>
        <div className="px-6 py-4 border-t border-white/10">
          <button
            onClick={onClose}
            className="w-full bg-[#380E75] text-[#DED5EB] font-syne font-bold uppercase tracking-wider rounded-full py-3 text-sm hover:bg-[#380E75]/80 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.12, duration: 0.6, ease: "easeOut" },
  }),
};

export default function LandingPage({ user }) {
  const navigate = useNavigate();
  const [modal, setModal] = useState(null);

  const handleStart = () => {
    if (user) {
      navigate("/dashboard");
    } else {
      navigate("/onboarding");
    }
  };

  return (
    <div
      className="hero-gradient min-h-screen relative overflow-hidden"
      data-testid="landing-page"
    >
      {modal === "terms" && <LegalModal title="Terms & Conditions" content={TERMS} onClose={() => setModal(null)} />}
      {modal === "privacy" && <LegalModal title="Privacy Policy" content={PRIVACY} onClose={() => setModal(null)} />}
      {/* Ambient light spots */}
      <div className="absolute top-0 left-[20%] w-[500px] h-[500px] bg-[#380E75]/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-[10%] w-[400px] h-[400px] bg-[#DED5EB]/4 rounded-full blur-[100px] pointer-events-none" />

      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-6 md:px-12 py-6">
        <div className="flex items-center gap-2">
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

        {user && (
          <Button
            variant="ghost"
            onClick={() => navigate("/dashboard")}
            className="text-sm text-zinc-400 hover:text-white"
            data-testid="go-to-dashboard-btn"
          >
            Dashboard
          </Button>
        )}
      </nav>

      {/* Hero */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 md:px-12 pt-20 md:pt-32 pb-20">
        <div className="max-w-3xl">
          <motion.p
            custom={0}
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            className="font-mono text-xs uppercase tracking-[0.2em] text-[#DED5EB]/80 mb-6"
            data-testid="hero-subtitle"
          >
            Concert Discovery Engine
          </motion.p>

          <motion.h1
            custom={1}
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            className="font-syne text-5xl md:text-7xl font-extrabold tracking-tight leading-[0.95] mb-8"
            data-testid="hero-title"
          >
            Find your next
            <br />
            <span className="text-[#DED5EB]">favorite show</span>
          </motion.h1>

          <motion.p
            custom={2}
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            className="text-lg md:text-xl text-zinc-400 leading-relaxed max-w-xl mb-12"
            data-testid="hero-description"
          >
            PAM analyzes your Spotify taste and discovers local concerts by
            independent artists you haven&apos;t heard yet — but will love.
          </motion.p>

          <motion.div
            custom={3}
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            className="flex flex-col sm:flex-row gap-4"
          >
            <Button
              onClick={handleStart}
              className="bg-[#380E75] text-[#DED5EB] font-syne font-bold uppercase tracking-wider rounded-full px-10 py-7 text-base hover:bg-[#380E75]/80 transition-all duration-200 hover:shadow-[0_0_25px_rgba(56,14,117,0.4)]"
              data-testid="get-started-btn"
            >
              <Sparkles className="w-5 h-5 mr-2" />
              {user ? "Go to Dashboard" : "Get Started"}
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </motion.div>
        </div>

        {/* Feature pills */}
        <motion.div
          custom={4}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="mt-24 grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          {[
            {
              icon: <Radio className="w-5 h-5 text-[#DED5EB]" />,
              title: "Taste Fingerprint",
              desc: "We build a deep profile from your top artists, genres, and audio preferences.",
            },
            {
              icon: <MapPin className="w-5 h-5 text-[#380E75]" />,
              title: "Local Discovery",
              desc: "Search concerts in your city. Filter by radius. Find hidden gems nearby.",
            },
            {
              icon: <Sparkles className="w-5 h-5 text-[#DED5EB]" />,
              title: "Smart Matching",
              desc: "Our algorithm scores every event against your taste. No noise, just signal.",
            },
          ].map((feature, i) => (
            <div
              key={i}
              className="glass-card p-6 group hover:border-white/10"
              data-testid={`feature-card-${i}`}
            >
              <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center mb-4 group-hover:bg-white/10 transition-colors duration-300">
                {feature.icon}
              </div>
              <h3 className="font-syne font-bold text-base mb-2">
                {feature.title}
              </h3>
              <p className="text-sm text-zinc-500 leading-relaxed">
                {feature.desc}
              </p>
            </div>
          ))}
        </motion.div>
      </div>

      {/* Footer */}
      <div className="relative z-10 border-t border-white/5 py-6 px-6 md:px-12 flex items-center justify-between">
        <p className="text-xs text-zinc-600 font-mono">
          PAM v1.0 — Powered by Spotify + Jambase
        </p>
        <div className="text-xs text-zinc-600 font-jakarta flex gap-4">
          <button onClick={() => setModal("terms")} className="underline hover:text-zinc-400 transition-colors">
            Terms & Conditions
          </button>
          <button onClick={() => setModal("privacy")} className="underline hover:text-zinc-400 transition-colors">
            Privacy Policy
          </button>
        </div>
      </div>
    </div>
  );
}
