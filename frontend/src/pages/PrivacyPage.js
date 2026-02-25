import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

export default function PrivacyPage() {
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
          Privacy Policy
        </h1>
        <p className="text-sm text-zinc-500 font-jakarta mb-10">
          Last updated: February 2026
        </p>

        <div className="space-y-8 text-zinc-400 font-jakarta text-sm leading-relaxed">
          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              1. Information We Collect
            </h2>
            <p className="mb-2">We collect the following information:</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>Name and email address (required to create an account)</li>
              <li>Phone number (optional, for SMS concert alerts)</li>
              <li>Spotify listening data: top artists and genre tags</li>
              <li>Location/city you enter when searching for concerts</li>
            </ul>
          </section>

          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              2. How We Use Your Information
            </h2>
            <ul className="list-disc list-inside space-y-1 ml-2 mb-3">
              <li>
                To build your music taste profile and match it against local
                concerts
              </li>
              <li>
                To send you SMS concert recommendations if you opt in
              </li>
              <li>To save your favorited concerts</li>
              <li>
                To generate a shareable taste profile if you choose to use that
                feature
              </li>
            </ul>
            <p>We do not sell your personal information to third parties.</p>
          </section>

          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              3. Third-Party Services
            </h2>
            <p className="mb-2">PAM integrates with the following services:</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>
                Spotify: to retrieve your listening data. Spotify's privacy
                policy applies to your Spotify account.
              </li>
              <li>
                Twilio: to send SMS messages if you provide a phone number.
              </li>
              <li>
                Jambase / Ticketmaster: to source concert event data.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              4. Data Storage
            </h2>
            <p>
              Your data is stored securely in a hosted database. We retain your
              data for as long as your account is active.
            </p>
          </section>

          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              5. Your Rights
            </h2>
            <p>
              You may request deletion of your account and associated data at
              any time by contacting us at{" "}
              <a
                href="mailto:hello@pamapp.com"
                className="text-[#DED5EB] underline hover:text-white transition-colors"
              >
                hello@pamapp.com
              </a>
              .
            </p>
          </section>

          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              6. SMS Opt-Out
            </h2>
            <p>
              If you provided a phone number and wish to stop receiving SMS
              messages, contact us at{" "}
              <a
                href="mailto:hello@pamapp.com"
                className="text-[#DED5EB] underline hover:text-white transition-colors"
              >
                hello@pamapp.com
              </a>{" "}
              and we will remove your number.
            </p>
          </section>

          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              7. Changes
            </h2>
            <p>
              We may update this policy periodically. We will notify you of
              significant changes via email.
            </p>
          </section>

          <section>
            <h2 className="font-syne font-bold text-base text-white mb-2">
              8. Contact
            </h2>
            <p>
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
