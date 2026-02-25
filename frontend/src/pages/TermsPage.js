import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

export default function TermsPage() {
  const navigate = useNavigate();

  return (
    <div className="hero-gradient min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 md:px-12 py-6">
        <div className="flex items-center gap-2">
          <img
            src={`${process.env.PUBLIC_URL}/PAM_logo_nav.png`}
            alt="PAM"
            className="w-10 h-10"
          />
          <span className="font-syne font-extrabold text-xl tracking-tight">
            PAM
          </span>
        </div>
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
      </nav>

      {/* Content */}
      <div className="flex-1 max-w-2xl mx-auto w-full px-6 md:px-12 py-12">
        <h1 className="font-syne font-extrabold text-3xl md:text-4xl text-white mb-2">
          Terms &amp; Conditions
        </h1>
        <p className="text-sm text-zinc-500 font-jakarta mb-10">
          Last updated: February 2026
        </p>

        <div className="space-y-8 text-zinc-400 font-jakarta text-sm leading-relaxed">
          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              1. Acceptance
            </h2>
            <p>
              By creating a PAM account you agree to these terms. If you do not
              agree, do not use the service.
            </p>
          </section>

          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              2. What PAM Does
            </h2>
            <p>
              PAM connects to your Spotify account to build a taste profile and
              uses that profile to suggest local concerts that match your music
              preferences. If you provide a phone number, PAM may send you SMS
              concert recommendations.
            </p>
          </section>

          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              3. SMS Notifications
            </h2>
            <p>
              By providing your phone number you consent to receiving automated
              SMS messages from PAM containing concert suggestions. Message
              frequency is based on your stated concert preferences. Message and
              data rates may apply. You can opt out at any time by contacting us
              or removing your phone number from your profile.
            </p>
          </section>

          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              4. Spotify Data
            </h2>
            <p>
              PAM accesses your Spotify listening data (top artists and genres)
              solely to generate concert recommendations. We do not share your
              Spotify data with third parties.
            </p>
          </section>

          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              5. Ticket Purchases
            </h2>
            <p>
              PAM provides links to third-party ticketing platforms. We are not
              responsible for any transactions made on those platforms.
            </p>
          </section>

          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              6. Limitation of Liability
            </h2>
            <p>
              PAM is provided as-is. We make no guarantees about the accuracy or
              availability of concert information. We are not liable for any
              losses arising from use of the service.
            </p>
          </section>

          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              7. Changes
            </h2>
            <p>
              We may update these terms at any time. Continued use of PAM after
              changes constitutes acceptance.
            </p>
          </section>

          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              8. Contact
            </h2>
            <p>
              For questions email us at{" "}
              <a
                href="mailto:hello@pamapp.com"
                className="text-[#DED5EB] underline hover:text-white transition-colors"
              >
                hello@pamapp.com
              </a>
            </p>
          </section>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-white/5 py-6 px-6 md:px-12 text-center">
        <p className="text-xs text-zinc-600 font-mono">
          PAM v1.0 — Powered by Spotify + Jambase
        </p>
      </div>
    </div>
  );
}
