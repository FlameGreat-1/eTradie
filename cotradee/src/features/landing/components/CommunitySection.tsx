import { memo } from 'react';
import { Facebook, MessageCircle, Send, MessageSquare, ExternalLink } from 'lucide-react';
import { useCommunityLinks, type CommunityLink, type CommunityPlatform } from '@/features/support';

/**
 * Landing-page community section.
 *
 * Renders the four Facebook / Discord / Telegram / WhatsApp public
 * channels in a panel matched to the landing-page visual idiom
 * (slate/dark surfaces, Inter typography). Deliberately does NOT
 * delegate to features/support/CommunityLinks because that component
 * is built for the dashboard chrome (design-token semantic surfaces),
 * which would clash with the landing palette.
 *
 * Both surfaces consume the same useCommunityLinks() TanStack Query
 * hook so there is one source of truth for the configured URLs.
 *
 * When the gateway exposes zero community URLs the section renders
 * nothing so a partially-configured deployment does not show an
 * empty placeholder.
 */
function CommunitySection() {
  const { data, isLoading } = useCommunityLinks();
  const links = data?.links ?? [];

  // Skeleton: shown while the initial fetch is in flight so the
  // section reserves height and the page does not jitter on first
  // paint. We intentionally do not show a 'loading' spinner; the
  // landing page is content-first and a skeleton card is more honest.
  if (isLoading) {
    return (
      <section
        id="community"
        className="relative py-24 border-t border-slate-200 dark:border-white/5 bg-slate-50/50 dark:bg-[#050505]"
      >
        <div className="max-w-[1280px] mx-auto px-6 md:px-8">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-white mb-4">
              Join the Community
            </h2>
            <p className="text-lg text-slate-600 dark:text-white/60 leading-relaxed">
              Connect with other Exoper traders on our public channels.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-5xl mx-auto">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-32 rounded-2xl border border-slate-200 dark:border-white/5 bg-white dark:bg-[#0c0c0c] animate-pulse"
              />
            ))}
          </div>
        </div>
      </section>
    );
  }

  if (links.length === 0) {
    return null;
  }

  return (
    <section
      id="community"
      className="relative py-24 border-t border-slate-200 dark:border-white/5 bg-slate-50/50 dark:bg-[#050505]"
      aria-labelledby="community-heading"
    >
      <div className="max-w-[1280px] mx-auto px-6 md:px-8">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <h2
            id="community-heading"
            className="text-3xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-white mb-4"
          >
            Join the Community
          </h2>
          <p className="text-lg text-slate-600 dark:text-white/60 leading-relaxed">
            Connect with other Exoper traders, get product updates, and join the conversation on our public channels.
            These channels are open to anyone — no account required.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-5xl mx-auto">
          {links.map((link) => (
            <CommunityCard key={link.platform} link={link} />
          ))}
        </div>
      </div>
    </section>
  );
}

/**
 * Per-platform metadata. Brand colours come from the theme-aware
 * `social-<platform>` Tailwind tokens (declared in tailwind.config.ts
 * and backed by CSS variables in src/assets/index.css), so the icon
 * tint is correct in both themes without per-component overrides.
 */
const PLATFORM_META: Record<
  CommunityPlatform,
  { icon: React.ReactNode; label: string; tagline: string; iconBg: string; iconColor: string }
> = {
  facebook: {
    icon: <Facebook size={22} />,
    label: 'Facebook',
    tagline: 'Latest announcements & community posts',
    iconBg: 'bg-social-facebook/14',
    iconColor: 'text-social-facebook',
  },
  discord: {
    icon: <MessageSquare size={22} />,
    label: 'Discord',
    tagline: 'Real-time chat with traders & the team',
    iconBg: 'bg-social-discord/14',
    iconColor: 'text-social-discord',
  },
  telegram: {
    icon: <Send size={22} />,
    label: 'Telegram',
    tagline: 'Instant updates & feature drops',
    iconBg: 'bg-social-telegram/14',
    iconColor: 'text-social-telegram',
  },
  whatsapp: {
    icon: <MessageCircle size={22} />,
    label: 'WhatsApp',
    tagline: 'Mobile-first broadcast channel',
    iconBg: 'bg-social-whatsapp/14',
    iconColor: 'text-social-whatsapp',
  },
};

function CommunityCard({ link }: { link: CommunityLink }) {
  const meta = PLATFORM_META[link.platform];
  return (
    <a
      href={link.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex flex-col gap-3 rounded-2xl border border-slate-200 dark:border-white/5
                 bg-white dark:bg-[#0c0c0c] p-5 shadow-md dark:shadow-xl
                 hover:border-slate-300 dark:hover:border-white/15
                 transition-colors duration-300"
    >
      <div className="flex items-center justify-between">
        <span
          className={`flex items-center justify-center w-11 h-11 rounded-xl ${meta.iconBg} ${meta.iconColor}`}
        >
          {meta.icon}
        </span>
        <ExternalLink
          size={14}
          className="text-slate-400 dark:text-white/40 group-hover:text-slate-700 dark:group-hover:text-white/80 transition-colors duration-300"
          aria-hidden
        />
      </div>
      <span className="text-base font-bold text-slate-900 dark:text-white">{meta.label}</span>
      <span className="text-sm text-slate-600 dark:text-white/60 leading-relaxed">{meta.tagline}</span>
    </a>
  );
}

export default memo(CommunitySection);
