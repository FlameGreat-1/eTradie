import { memo } from 'react';
import SupportCenter from '@/features/support/SupportCenter';

/**
 * /dashboard/support is rendered by AppRoutes inside the authenticated
 * DashboardLayout. The page itself is a thin wrapper around
 * SupportCenter so the ticketing experience can be reused from any
 * other authenticated surface (for example a future help-widget
 * overlay) without page-level coupling.
 */
function SupportPage() {
  return <SupportCenter />;
}

export default memo(SupportPage);
