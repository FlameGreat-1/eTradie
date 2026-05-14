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
    <p
      role="alert"
      className="mt-1 text-xs text-status-danger"
    >
      {message}
    </p>
  );
}

export const FieldError = memo(FieldErrorInner);
