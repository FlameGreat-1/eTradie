/**
 * Visual separator between primary credentials and social-auth
 * options. Pure presentation; no state or behaviour.
 */
export default function SocialAuthDivider({ label = 'or continue with' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 my-2" role="separator" aria-label={label}>
      <span className="flex-1 h-px bg-border" aria-hidden="true" />
      <span className="text-[11px] uppercase tracking-wider text-content-muted">{label}</span>
      <span className="flex-1 h-px bg-border" aria-hidden="true" />
    </div>
  );
}
