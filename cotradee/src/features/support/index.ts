// Public barrel for the support feature. Consumers (pages, layout
// fragments, the landing footer) import from '@/features/support' so
// the internal file layout can move without forcing call-site churn.
export * from './types';
export * from './api/support';
export { default as CommunityLinks } from './components/CommunityLinks';
export { default as ContactForm } from './components/ContactForm';
export { default as TicketList } from './components/TicketList';
export { default as TicketDetail } from './components/TicketDetail';
export { default as NewTicketModal } from './components/NewTicketModal';
export { default as SupportCenter } from './SupportCenter';
