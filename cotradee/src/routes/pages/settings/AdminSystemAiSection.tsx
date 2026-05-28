import { AdminProcessorConfigPanel } from '@/features/admin/components/AdminProcessorConfigPanel';
import { AdminQuotaPolicyPanel } from '@/features/admin/components/AdminQuotaPolicyPanel';

export default function AdminSystemAiSection() {
  return (
    <div className="space-y-10 max-w-7xl">
      <AdminProcessorConfigPanel />
      {/*
        Admin tier-quota policy editor (Audit ref: ADMIN-QUOTA-14).

        Backs the tier_quota_policies table (migration 0028). Renders
        ONLY pro_managed + admin tier cards because, per the QUOTA.md
        scope decision, free and pro_byok tiers are BYOK by design and
        have no platform quota to edit. The panel's internal hooks
        gate every fetch on isAdmin as defense-in-depth even though
        the parent Settings route already enforces admin access.
      */}
      <AdminQuotaPolicyPanel />
    </div>
  );
}
