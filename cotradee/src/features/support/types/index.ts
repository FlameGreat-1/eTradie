/**
 * Wire shapes for the Support module. These mirror src/support/models.go
 * one-to-one; the field names and enum literals must stay aligned so
 * the SPA and gateway never disagree on what a ticket looks like.
 *
 * The TICKET_* arrays are exported as `as const` so the form
 * components can iterate them without re-declaring the values, and so
 * TypeScript narrows them to the literal union rather than the wide
 * `string` type.
 */

export const TICKET_STATUSES = [
  'open',
  'pending',
  'resolved',
  'closed',
] as const;
export type TicketStatus = (typeof TICKET_STATUSES)[number];

export const TICKET_PRIORITIES = [
  'low',
  'normal',
  'high',
  'urgent',
] as const;
export type TicketPriority = (typeof TICKET_PRIORITIES)[number];

export const TICKET_CATEGORIES = [
  'general',
  'billing',
  'technical',
  'account',
  'feedback',
  'bug',
  'feature',
  'security',
  'complaint',
] as const;
export type TicketCategory = (typeof TICKET_CATEGORIES)[number];

export const TICKET_CHANNELS = ['web', 'contact', 'email'] as const;
export type TicketChannel = (typeof TICKET_CHANNELS)[number];

export const MESSAGE_AUTHOR_KINDS = ['user', 'staff', 'system'] as const;
export type MessageAuthorKind = (typeof MESSAGE_AUTHOR_KINDS)[number];

export const COMMUNITY_PLATFORMS = [
  'facebook',
  'discord',
  'telegram',
  'whatsapp',
] as const;
export type CommunityPlatform = (typeof COMMUNITY_PLATFORMS)[number];

/** A single entry in a ticket's append-only conversation log. */
export interface TicketMessage {
  id: string;
  ticket_id: string;
  author_kind: MessageAuthorKind;
  author_id?: string;
  body: string;
  created_at: string;
}

/** Canonical ticket record returned by every server response. */
export interface Ticket {
  id: string;
  public_ref: string;
  user_id?: string;
  email: string;
  name?: string;
  subject: string;
  category: TicketCategory;
  priority: TicketPriority;
  status: TicketStatus;
  channel: TicketChannel;
  created_at: string;
  updated_at: string;
  closed_at?: string;
  messages?: TicketMessage[];
}

/** Response envelope for the list endpoint. */
export interface TicketListResponse {
  tickets: Ticket[];
  limit: number;
  offset: number;
}

/** Response envelope used by the create / get / close endpoints. */
export interface TicketResponse {
  ticket: Ticket;
}

/** Response envelope used by the append-message endpoint. */
export interface AppendMessageResponse {
  message: TicketMessage;
  ticket: Ticket;
}

/** A single community-link entry. */
export interface CommunityLink {
  platform: CommunityPlatform;
  url: string;
}

export interface CommunityLinksResponse {
  links: CommunityLink[];
}

/** Public contact form input. */
export interface ContactFormInput {
  email: string;
  name?: string;
  subject: string;
  message: string;
  category?: TicketCategory;
  priority?: TicketPriority;
}

/** Authenticated 'new ticket from dashboard' input. */
export interface NewTicketInput {
  subject: string;
  message: string;
  category?: TicketCategory;
  priority?: TicketPriority;
}

/** Authenticated reply input. */
export interface ReplyInput {
  message: string;
}

/** UI-friendly display labels keyed by enum value. Kept here so the
 * mapping is shared by every component that renders a badge / select. */
export const STATUS_LABELS: Record<TicketStatus, string> = {
  open: 'Open',
  pending: 'Pending',
  resolved: 'Resolved',
  closed: 'Closed',
};

export const PRIORITY_LABELS: Record<TicketPriority, string> = {
  low: 'Low',
  normal: 'Normal',
  high: 'High',
  urgent: 'Urgent',
};

export const CATEGORY_LABELS: Record<TicketCategory, string> = {
  general: 'General enquiry',
  billing: 'Billing & subscription',
  technical: 'Technical issue',
  account: 'Account & access',
  feedback: 'Feedback',
  bug: 'Bug report',
  feature: 'Feature request',
  security: 'Security concern',
  complaint: 'Complaint',
};

export const COMMUNITY_LABELS: Record<CommunityPlatform, string> = {
  facebook: 'Facebook',
  discord: 'Discord',
  telegram: 'Telegram',
  whatsapp: 'WhatsApp',
};
