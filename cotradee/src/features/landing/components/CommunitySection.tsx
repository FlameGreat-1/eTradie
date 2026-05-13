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
                className="h-64 rounded-2xl border border-border bg-surface-1 animate-pulse"
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
      className="relative py-24 border-t border-border bg-surface-0"
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
      className="feature-card group h-full"
    >
      <div className="feature-card-header">
        <span className={`feature-card-icon ${meta.iconColor}`}>
          {meta.icon}
        </span>
        <span className="feature-card-publisher">Official Community</span>
      </div>

      <div className="flex-1">
        <h3 className="feature-card-title">{meta.label}</h3>
        <p className="feature-card-desc">{meta.tagline}</p>
      </div>

      <div className="feature-card-tags">
        <span className="feature-card-chip">community</span>
        <span className="feature-card-chip">real-time</span>
      </div>

      <ExternalLink
        size={14}
        className="absolute top-6 right-6 text-content-faint group-hover:text-brand transition-colors duration-fast"
        aria-hidden
      />
    </a>
  );
}

export default memo(CommunitySection);
