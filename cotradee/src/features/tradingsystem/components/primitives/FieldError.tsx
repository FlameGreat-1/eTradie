import { memo } from 'react';

interface Props {
  message?: string;
}

/**
 * Inline server-side field error. Renders nothing when the message
 * is empty so callers can render unconditionally.
 */
function FieldErrorInner({ message }: Props) {
  if (!message) return null;
  return (
    <div
      role="alert"
      className="mt-2 flex items-center gap-1.5 rounded-lg bg-danger/10 px-3 py-2 text-[11px] font-bold text-danger animate-in fade-in slide-in-from-top-1 duration-200"
    >
      <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      {message}
    </div>
  );
}

export const FieldError = memo(FieldErrorInner);
