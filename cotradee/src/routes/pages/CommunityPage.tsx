import { memo } from 'react';
import CommunityLinks from '@/features/support/components/CommunityLinks';

/**
 * CommunityPage provides a dedicated surface for users to connect
 * with the eTradie ecosystem across official channels (Discord, 
 * Telegram, etc.).
 */
function CommunityPage() {
  return (
    <div className="h-full overflow-auto p-4 sm:p-8 animate-fade-in bg-surface-1">
      <div className="max-w-5xl mx-auto space-y-8">
        <header className="space-y-1.5">
          <h1 className="text-2xl font-bold text-content">Official Community</h1>
          <p className="text-sm text-content-muted">
            Connect with other eTradie users and get real-time updates on our public channels.
          </p>
        </header>

        <CommunityLinks />
        
        <footer className="pt-8 border-t border-border/30 text-center">
          <p className="text-[11px] text-content-muted">
            These are public channels for community discussion. For account-specific help, please use the Support Centre.
          </p>
        </footer>
      </div>
    </div>
  );
}

export default memo(CommunityPage);
