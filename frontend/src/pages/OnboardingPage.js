import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Music, ArrowRight, ArrowLeft, User, DollarSign, Calendar, MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { api } from "@/lib/api";

export default function OnboardingPage({ onSaveUser }) {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: "",
    email: "",
    city: "",
    concerts_per_month: 2,
    ticket_budget: 50,
  });

  const updateField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleNext = () => {
    if (step === 1) {
      if (!form.name.trim()) {
        toast.error("Please enter your name");
        return;
      }
      if (!form.email.trim() || !form.email.includes("@")) {
        toast.error("Please enter a valid email");
        return;
      }
      if (!form.city.trim() || !form.city.includes(",")) {
        toast.error("Please enter your location as City, State (e.g. Roanoke, VA)");
        return;
      }
    }
    setStep(2);
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const res = await api.createUser({
        name: form.name,
        email: form.email,
        city: form.city.trim(),
        concerts_per_month: form.concerts_per_month,
        ticket_budget: form.ticket_budget,
      });
      const user = res.data;
      onSaveUser(user);
      toast.success("Profile created! Let's connect your Spotify.");

      // Initiate Spotify login - use top-level navigation to escape iframe
      const spotifyRes = await api.spotifyLogin(user.id);
      const authUrl = spotifyRes.data.auth_url;
      try {
        if (window.top !== window.self) {
          window.top.location.href = authUrl;
        } else {
          window.location.href = authUrl;
        }
      } catch {
        window.open(authUrl, '_blank');
      }
    } catch (err) {
      console.error(err);
      toast.error("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const slideVariants = {
    enter: { x: 40, opacity: 0 },
    center: { x: 0, opacity: 1 },
    exit: { x: -40, opacity: 0 },
  };

  return (
    <div className="hero-gradient min-h-screen flex flex-col" data-testid="onboarding-page">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 md:px-12 py-6">
        <div className="flex items-center gap-2">
          <img src={`${process.env.PUBLIC_URL}/PAM_logo_nav.png`} alt="PAM" className="w-10 h-10" />
          </div>
          <span className="font-syne font-extrabold text-xl tracking-tight">PAM</span>
          <span className="text-sm text-zinc-500 ml-2">Your concert buddy</span>
        </div>
        <Button
          variant="ghost"
          onClick={() => navigate("/")}
          className="text-sm text-zinc-400 hover:text-white"
          data-testid="back-home-btn"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back
        </Button>
      </nav>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center px-6 pb-12">
        <div className="w-full max-w-md">
          {/* Progress */}
          <div className="flex gap-2 mb-10">
            {[1, 2].map((s) => (
              <div
                key={s}
                className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
                  s <= step ? "bg-[#380E75]" : "bg-white/10"
                }`}
                data-testid={`progress-step-${s}`}
              />
            ))}
          </div>

          <AnimatePresence mode="wait">
            {step === 1 && (
              <motion.div
                key="step1"
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.3 }}
              >
                <div className="mb-8">
                  <p className="font-mono text-xs uppercase tracking-[0.2em] text-[#DED5EB]/80 mb-3">
                    Step 1 of 2
                  </p>
                  <h2 className="font-syne text-3xl md:text-4xl font-bold tracking-tight mb-2">
                    Tell us about you
                  </h2>
                  <p className="text-zinc-500 text-sm">
                    Basic info so we can save your taste profile.
                  </p>
                </div>

                <div className="space-y-5">
                  <div>
                    <Label htmlFor="name" className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-2 flex items-center gap-2">
                      <User className="w-3.5 h-3.5" /> Your Name
                    </Label>
                    <Input
                      id="name"
                      placeholder="e.g. Jordan"
                      value={form.name}
                      onChange={(e) => updateField("name", e.target.value)}
                      className="bg-secondary/50 border-white/10 h-12 px-4 font-jakarta text-sm placeholder:text-zinc-600 rounded-lg"
                      data-testid="name-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="email" className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-2 flex items-center gap-2">
                      <span>@</span> Email
                    </Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="you@email.com"
                      value={form.email}
                      onChange={(e) => updateField("email", e.target.value)}
                      className="bg-secondary/50 border-white/10 h-12 px-4 font-jakarta text-sm placeholder:text-zinc-600 rounded-lg"
                      data-testid="email-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="city" className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-2 flex items-center gap-2">
                      <MapPin className="w-3.5 h-3.5" /> Location
                    </Label>
                    <Input
                      id="city"
                      placeholder="e.g. Roanoke, VA"
                      value={form.city}
                      onChange={(e) => updateField("city", e.target.value)}
                      className="bg-secondary/50 border-white/10 h-12 px-4 font-jakarta text-sm placeholder:text-zinc-600 rounded-lg"
                      data-testid="city-input"
                    />
                  </div>
                </div>

                <Button
                  onClick={handleNext}
                  className="w-full mt-8 bg-[#380E75] text-[#DED5EB] font-syne font-bold uppercase tracking-wider rounded-full py-6 hover:bg-[#380E75]/80 transition-colors duration-200"
                  data-testid="next-step-btn"
                >
                  Continue
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div
                key="step2"
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.3 }}
              >
                <div className="mb-8">
                  <p className="font-mono text-xs uppercase tracking-[0.2em] text-[#DED5EB]/80 mb-3">
                    Step 2 of 2
                  </p>
                  <h2 className="font-syne text-3xl md:text-4xl font-bold tracking-tight mb-2">
                    Concert preferences
                  </h2>
                  <p className="text-zinc-500 text-sm">
                    How often do you want to go out, and what's your budget?
                  </p>
                </div>

                <div className="space-y-8">
                  <div>
                    <Label className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-4 flex items-center gap-2">
                      <Calendar className="w-3.5 h-3.5" /> Concerts per month
                    </Label>
                    <div className="flex items-center gap-4">
                      <Slider
                        value={[form.concerts_per_month]}
                        onValueChange={([val]) => updateField("concerts_per_month", val)}
                        min={1}
                        max={10}
                        step={1}
                        className="flex-1"
                        data-testid="concerts-slider"
                      />
                      <span className="font-mono text-[#DED5EB] text-lg font-bold w-8 text-center" data-testid="concerts-value">
                        {form.concerts_per_month}
                      </span>
                    </div>
                  </div>

                  <div>
                    <Label className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-4 flex items-center gap-2">
                      <DollarSign className="w-3.5 h-3.5" /> Budget per show
                    </Label>
                    <div className="flex items-center gap-4">
                      <Slider
                        value={[form.ticket_budget]}
                        onValueChange={([val]) => updateField("ticket_budget", val)}
                        min={10}
                        max={200}
                        step={5}
                        className="flex-1"
                        data-testid="budget-slider"
                      />
                      <span className="font-mono text-[#DED5EB] text-lg font-bold w-16 text-right" data-testid="budget-value">
                        ${form.ticket_budget}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3 mt-10">
                  <Button
                    variant="ghost"
                    onClick={() => setStep(1)}
                    className="text-zinc-400 hover:text-white rounded-full px-6 py-6"
                    data-testid="back-step-btn"
                  >
                    <ArrowLeft className="w-4 h-4 mr-1" /> Back
                  </Button>
                  <Button
                    onClick={handleSubmit}
                    disabled={loading}
                    className="flex-1 bg-[#380E75] text-[#DED5EB] font-syne font-bold uppercase tracking-wider rounded-full py-6 text-base hover:bg-[#380E75]/80 transition-all duration-200 hover:shadow-[0_0_25px_rgba(56,14,117,0.4)] disabled:opacity-50"
                    data-testid="connect-spotify-btn"
                  >
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <span className="w-4 h-4 border-2 border-[#DED5EB]/30 border-t-[#DED5EB] rounded-full animate-spin" />
                        Connecting...
                      </span>
                    ) : (
                      <>
                        <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                        </svg>
                        Connect Spotify
                      </>
                    )}
                  </Button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
