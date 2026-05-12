import { memo } from 'react';
import { Facebook, MessageCircle, Send, MessageSquare, ExternalLink } from 'lucide-react';
import { COMMUNITY_LABELS, useCommunityLinks, type CommunityLink, type CommunityPlatform } from '@/features/support';

/**
 * CommunityLinks renders a 4-up responsive grid of the public
 * Facebook / Discord / Telegram / WhatsApp entry points configured
 * for the platform.
 *
 * The grid is hidden entirely when the gateway has no community URLs
 * configured so partial deployments do not show empty placeholders.
 * A skeleton row is shown while the initial fetch is in flight to
 * avoid layout shift on first paint.
 */
function CommunityLinks({
  heading = 'Join our community',
  description = 'Connect with other Exoper users and get real-time updates on the public channels below. These are distinct from our private support channels.',
  className = '',
}: {
  heading?: string;
  description?: string;
  className?: string;
}) {
  const { data, isLoading } = useCommunityLinks();

  if (isLoading) {
    return (
      <section className={`rounded-xl border border-border bg-surface-1 p-4 sm:p-6 ${className}`}>
        <h2 className="text-sm font-bold text-content mb-1">{heading}</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-24 rounded-xl border border-border bg-surface-2 animate-pulse" />
          ))}
        </div>
      </section>
    );
  }

  const links = data?.links ?? [];
  if (links.length === 0) {
    return null;
  }

  return (
    <section className={`rounded-xl border border-border bg-surface-1 p-4 sm:p-6 ${className}`} aria-labelledby="community-heading">
      <h2 id="community-heading" className="text-sm font-bold text-content mb-1">
        {heading}
      </h2>
      <p className="text-xs text-content-muted mb-4">{description}</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {links.map((link) => (
          <CommunityCard key={link.platform} link={link} />
        ))}
      </div>
    </section>
  );
}

// Each platform pulls its surface (/14 soft pill) and foreground glyph
// from the theme-aware `social.<platform>` tokens declared in
// tailwind.config.ts. The tokens automatically switch between dark and
// light theme values via the --social-<platform>-rgb CSS variables in
// src/assets/index.css.
const PLATFORM_META: Record<
  CommunityPlatform,
  { icon: React.ReactNode; iconBg: string; iconColor: string; tagline: string }
> = {
  facebook: {
    icon: <Facebook size={18} />,
    iconBg: 'bg-social-facebook/14',
    iconColor: 'text-social-facebook',
    tagline: 'Latest announcements & community posts',
  },
  discord: {
    icon: <MessageSquare size={18} />,
    iconBg: 'bg-social-discord/14',
    iconColor: 'text-social-discord',
    tagline: 'Real-time chat with traders & the team',
  },
  telegram: {
    icon: <Send size={18} />,
    iconBg: 'bg-social-telegram/14',
    iconColor: 'text-social-telegram',
    tagline: 'Instant updates & feature drops',
  },
  whatsapp: {
    icon: <MessageCircle size={18} />,
    iconBg: 'bg-social-whatsapp/14',
    iconColor: 'text-social-whatsapp',
    tagline: 'Mobile-first broadcast channel',
  },
};

function CommunityCard({ link }: { link: CommunityLink }) {
  const meta = PLATFORM_META[link.platform];
  return (
    <a
      href={link.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex flex-col gap-2.5 rounded-xl border border-border bg-surface-2 p-4
                 hover:border-brand transition-colors duration-fast focus-ring"
    >
      <div className="flex items-center justify-between">
        <span className={`flex items-center justify-center w-9 h-9 rounded-lg ${meta.iconBg} ${meta.iconColor}`}>
          {meta.icon}
        </span>
        <ExternalLink
          size={12}
          className="text-content-muted group-hover:text-brand transition-colors duration-fast"
          aria-hidden
        />
      </div>
      <span className="text-sm font-bold text-content">{COMMUNITY_LABELS[link.platform]}</span>
      <span className="text-[11px] text-content-muted leading-relaxed">{meta.tagline}</span>
    </a>
  );
}

export default memo(CommunityLinks);
