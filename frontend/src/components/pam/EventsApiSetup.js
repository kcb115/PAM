import { useState, useEffect } from "react";
import { Key, ExternalLink, Check, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { api } from "@/lib/api";

export const EventsApiSetup = ({ onConfigured }) => {
  const [hasKey, setHasKey] = useState(null);
  const [keyInput, setKeyInput] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getEventsApiStatus().then((res) => {
      setHasKey(res.data.has_events_api);
      if (res.data.has_events_api && onConfigured) onConfigured();
    }).catch(() => {});
  }, [onConfigured]);

  if (hasKey === null) return null;
  if (hasKey) return null;

  const handleSave = async () => {
    if (!keyInput.trim()) return;
    setSaving(true);
    try {
      const res = await api.setTicketmasterKey(keyInput.trim());
      if (res.data.success) {
        setHasKey(true);
        toast.success(res.data.message);
        if (onConfigured) onConfigured();
      } else {
        toast.error(res.data.message);
      }
    } catch (err) {
      toast.error("Failed to save key");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="glass-card p-6 mb-8 border border-[#380E75]/30" data-testid="events-api-setup">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-[#380E75]/20 flex items-center justify-center shrink-0">
          <Key className="w-5 h-5 text-[#DED5EB]" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-syne font-bold text-base text-white mb-1">
            Connect Events API
          </h3>
          <p className="text-xs text-zinc-400 mb-4 leading-relaxed">
            To see <strong>real upcoming concerts</strong> in your area, add a free Ticketmaster API key. 
            It takes 2 minutes — no credit card needed.
          </p>

          <div className="space-y-3">
            <a
              href="https://developer.ticketmaster.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs font-mono text-[#DED5EB] hover:underline"
              data-testid="ticketmaster-register-link"
            >
              1. Register at developer.ticketmaster.com
              <ExternalLink className="w-3 h-3" />
            </a>
            <p className="text-xs text-zinc-500 font-mono">
              2. Copy your "Consumer Key" from the dashboard
            </p>
            <p className="text-xs text-zinc-500 font-mono">
              3. Paste it below:
            </p>

            <div className="flex gap-2">
              <Input
                placeholder="Paste your Consumer Key here..."
                value={keyInput}
                onChange={(e) => setKeyInput(e.target.value)}
                className="bg-secondary/50 border-white/10 h-10 px-3 font-mono text-xs placeholder:text-zinc-600 rounded-lg flex-1"
                data-testid="ticketmaster-key-input"
              />
              <Button
                onClick={handleSave}
                disabled={saving || !keyInput.trim()}
                className="bg-[#380E75] text-[#DED5EB] font-syne font-bold rounded-lg h-10 px-6 hover:bg-[#380E75]/80 disabled:opacity-50"
                data-testid="save-key-btn"
              >
                {saving ? (
                  <span className="w-4 h-4 border-2 border-[#DED5EB]/30 border-t-[#DED5EB] rounded-full animate-spin" />
                ) : (
                  <>
                    <Check className="w-4 h-4 mr-1" />
                    Save
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
