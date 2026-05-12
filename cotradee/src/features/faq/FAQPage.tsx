import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronDown, Search, LifeBuoy } from 'lucide-react';
import '@/features/landing/landing.css';
import './faq.css';
import ParticlesCanvas from '@/features/landing/components/ParticlesCanvas';
import LandingHeader from '@/features/landing/components/LandingHeader';
import LandingFooter from '@/features/landing/components/LandingFooter';
import { FAQ_CATEGORIES, type FAQCategory, type FAQItem } from './data';

/**
 * Public /faq page.
 *
 * Visual chrome matches the LegalPageLayout pattern (landing.css,
 * ParticlesCanvas, LandingHeader, LandingFooter) so the page sits in
 * the same visual world as /pricing, /process, /terms, etc.
 *
 * The content surface is intentionally distinct from a legal
 * document:
 *   - sticky category sidebar (left) for navigation,
 *   - real-time search input,
 *   - accordion of Q&A items grouped by category.
 *
 * Deep linking: /faq#&lt;category-id&gt; or /faq#&lt;item-id&gt; scrolls to
 * the matching anchor on mount. Item ids auto-expand the accordion.
 */
function FAQPage() {
  const location = useLocation();
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  // Track whether the user has typed anything yet, so we can keep
  // the empty-state copy out of the way on first paint.
  const hasSearch = search.trim().length > 0;
  const normalisedSearch = useMemo(
    () => search.trim().toLowerCase(),
    [search],
  );

  // Compute the filtered view. When the search is empty we render
  // the full catalogue. Otherwise we keep only items whose question,
  // keyword list, or extracted answer text contains the search term.
  const filteredCategories = useMemo<FAQCategory[]>(() => {
    if (!normalisedSearch) return FAQ_CATEGORIES;
    const out: FAQCategory[] = [];
    for (const cat of FAQ_CATEGORIES) {
      const matchedItems = cat.items.filter((item) =>
        matchesSearch(item, normalisedSearch),
      );
      if (matchedItems.length > 0) {
        out.push({ ...cat, items: matchedItems });
      }
    }
    return out;
  }, [normalisedSearch]);

  // When the user runs a search we auto-expand every matching item
  // so the answers are visible immediately. Clearing the search
  // restores the collapsed default plus anything explicitly opened
  // by the user before the search began.
  const userExpandedRef = useRef<Set<string>>(new Set());
  useEffect(() => {
    if (!normalisedSearch) {
      setExpanded(new Set(userExpandedRef.current));
      return;
    }
    const next = new Set<string>(userExpandedRef.current);
    for (const cat of filteredCategories) {
      for (const item of cat.items) next.add(item.id);
    }
    setExpanded(next);
  }, [normalisedSearch, filteredCategories]);

  // Deep-link handling. Runs once on mount and again whenever the
  // URL hash changes (e.g. user clicks a sidebar entry that targets
  // a different fragment).
  useEffect(() => {
    const hash = location.hash.replace(/^#/, '');
    if (!hash) return;
    if (isItemId(hash)) {
      userExpandedRef.current.add(hash);
      setExpanded((prev) => {
        const next = new Set(prev);
        next.add(hash);
        return next;
      });
    }
    // Use a microtask so the accordion body has mounted before we
    // attempt to scroll to it.
    queueMicrotask(() => {
      const el = document.getElementById(hash);
      if (el) el.scrollIntoView({ block: 'start' });
    });
  }, [location.hash]);

  const toggle = useCallback((id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
        userExpandedRef.current.delete(id);
      } else {
        next.add(id);
        userExpandedRef.current.add(id);
      }
      return next;
    });
  }, []);

  const totalVisible = filteredCategories.reduce(
    (n, c) => n + c.items.length,
    0,
  );

  return (
    <div className="landing-page">
      <ParticlesCanvas />
      <div className="landing-content">
        <LandingHeader forceScrolled />

        <main className="w-full max-w-[1100px] mx-auto px-6 pt-32 pb-32">
          {/* Breadcrumb */}
          <nav className="flex items-center gap-2 text-xs mb-10" aria-label="Breadcrumb">
            <Link
              to="/landing"
              className="transition-colors duration-150"
              style={{ color: 'var(--landing-text-faint)' }}
            >
              Home
            </Link>
            <span style={{ color: 'var(--landing-text-faint)' }}>›</span>
            <span style={{ color: 'var(--landing-text)' }}>FAQs</span>
          </nav>

          {/* Page header */}
          <div className="mb-12">
            <div className="inline-flex items-center gap-2 mb-4">
              <span
                className="text-[10px] font-bold uppercase tracking-[0.25em] px-3 py-1 rounded-full"
                style={{
                  background: 'rgba(118,185,0,0.12)',
                  color: '#76b900',
                  border: '1px solid rgba(118,185,0,0.25)',
                }}
              >
                Frequently Asked Questions
              </span>
            </div>
            <h1
              className="text-3xl md:text-4xl font-bold tracking-tight mb-3"
              style={{ color: 'var(--landing-text)' }}
            >
              Answers to common questions
            </h1>
            <p className="text-base max-w-2xl" style={{ color: 'var(--landing-text-faint)' }}>
              Quick answers about how Exoper works, plans and billing, broker connections, security, and support.
              If you cannot find what you need, our team is one click away.
            </p>
          </div>

          {/* Divider */}
          <div
            className="w-full h-[1px] mb-12"
            style={{
              background:
                'linear-gradient(to right, transparent, var(--landing-card-border), transparent)',
            }}
          />

          {/* Two-column layout */}
          <div className="flex flex-col lg:flex-row gap-12">
            {/* Sticky category sidebar */}
            <aside className="lg:w-56 flex-shrink-0">
              <div className="lg:sticky lg:top-28">
                <p
                  className="text-[10px] font-bold uppercase tracking-[0.25em] mb-4"
                  style={{ color: 'var(--landing-text-faint)' }}
                >
                  Categories
                </p>
                <nav className="flex flex-col gap-1" aria-label="FAQ categories">
                  {FAQ_CATEGORIES.map((cat) => (
                    <a
                      key={cat.id}
                      href={`#${cat.id}`}
                      className="text-sm py-1.5 px-3 rounded-lg transition-colors duration-150 block"
                      style={{ color: 'var(--landing-text-faint)' }}
                      onMouseOver={(e) => {
                        (e.currentTarget as HTMLElement).style.color = 'var(--landing-text)';
                        (e.currentTarget as HTMLElement).style.background =
                          'var(--landing-card-bg)';
                      }}
                      onMouseOut={(e) => {
                        (e.currentTarget as HTMLElement).style.color = 'var(--landing-text-faint)';
                        (e.currentTarget as HTMLElement).style.background = 'transparent';
                      }}
                    >
                      {cat.title}
                    </a>
                  ))}
                </nav>
              </div>
            </aside>

            {/* Document body */}
            <article className="flex-1 min-w-0 faq-body" style={{ color: 'var(--landing-text)' }}>
              {/* Search */}
              <div className="relative mb-10">
                <Search
                  size={14}
                  className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                  style={{ color: 'var(--landing-text-faint)' }}
                  aria-hidden
                />
                <input
                  type="search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search the FAQs\u2026"
                  aria-label="Search the FAQs"
                  className="faq-search-input"
                />
                {hasSearch && (
                  <p
                    className="text-[11px] mt-2"
                    style={{ color: 'var(--landing-text-faint)' }}
                    aria-live="polite"
                  >
                    {totalVisible === 0
                      ? 'No matches.'
                      : `${totalVisible} match${totalVisible === 1 ? '' : 'es'}.`}
                  </p>
                )}
              </div>

              {/* Empty state */}
              {totalVisible === 0 && (
                <div className="faq-empty">
                  <p style={{ marginBottom: '0.75rem' }}>
                    We could not find anything matching
                    {' \u201C'}
                    <strong style={{ color: 'var(--landing-text)' }}>{search.trim()}</strong>
                    {'\u201D'}
                    .
                  </p>
                  <p style={{ marginBottom: '1.25rem' }}>
                    Try a different keyword, or reach out to our team directly.
                  </p>
                  <Link
                    to="/contact"
                    className="inline-flex items-center gap-2 text-sm font-semibold"
                    style={{ color: '#76b900' }}
                  >
                    <LifeBuoy size={14} /> Contact us
                  </Link>
                </div>
              )}

              {/* Categories + items */}
              {filteredCategories.map((cat) => (
                <section
                  key={cat.id}
                  id={cat.id}
                  className="faq-category"
                  aria-labelledby={`${cat.id}-title`}
                >
                  <h2 id={`${cat.id}-title`} className="faq-category-title">
                    {cat.title}
                  </h2>
                  <p className="faq-category-description">{cat.description}</p>
                  <div>
                    {cat.items.map((item) => (
                      <AccordionRow
                        key={item.id}
                        item={item}
                        expanded={expanded.has(item.id)}
                        onToggle={() => toggle(item.id)}
                      />
                    ))}
                  </div>
                </section>
              ))}

              {/* Footer CTA */}
              <div
                className="mt-16 rounded-2xl px-6 py-8 text-center"
                style={{
                  background: 'var(--landing-card-bg)',
                  border: '1px solid var(--landing-card-border)',
                }}
              >
                <h2
                  className="text-lg font-bold mb-2"
                  style={{ color: 'var(--landing-text)' }}
                >
                  Still need help?
                </h2>
                <p
                  className="text-sm mb-5 max-w-xl mx-auto"
                  style={{ color: 'var(--landing-text-faint)' }}
                >
                  Our team typically responds within one business day. For account-specific issues please open a support ticket so we can verify your account.
                </p>
                <Link
                  to="/contact"
                  className="inline-flex items-center gap-2 px-5 h-10 rounded-lg text-sm font-semibold"
                  style={{
                    background: '#76b900',
                    color: '#0a0a0a',
                  }}
                >
                  <LifeBuoy size={14} /> Contact support
                </Link>
              </div>
            </article>
          </div>
        </main>

        <LandingFooter />
      </div>
    </div>
  );
}

function AccordionRow({
  item,
  expanded,
  onToggle,
}: {
  item: FAQItem;
  expanded: boolean;
  onToggle: () => void;
}) {
  const panelId = `${item.id}-panel`;
  return (
    <div className="faq-item" data-expanded={expanded}>
      <button
        type="button"
        id={item.id}
        className="faq-item-trigger"
        onClick={onToggle}
        aria-expanded={expanded}
        aria-controls={panelId}
      >
        <span>{item.question}</span>
        <ChevronDown className="faq-item-icon" aria-hidden />
      </button>
      {expanded && (
        <div
          id={panelId}
          role="region"
          aria-labelledby={item.id}
          className="faq-item-panel"
        >
          {typeof item.answer === 'string' ? <p>{item.answer}</p> : item.answer}
        </div>
      )}
    </div>
  );
}

/**
 * matchesSearch performs a case-insensitive substring match against
 * the question, the answer (when it is a plain string), and the
 * optional keyword list. Non-string answers are matched only via
 * the question + keywords so we never run a full DOM render to
 * extract text.
 */
function matchesSearch(item: FAQItem, term: string): boolean {
  if (item.question.toLowerCase().includes(term)) return true;
  if (typeof item.answer === 'string' && item.answer.toLowerCase().includes(term)) {
    return true;
  }
  if (item.keywords) {
    for (const k of item.keywords) {
      if (k.toLowerCase().includes(term)) return true;
    }
  }
  return false;
}

/**
 * Quick predicate used by the hash handler: returns true if the
 * given string matches the id of an FAQ item (rather than a
 * category). The check is O(items) once per hash change.
 */
function isItemId(id: string): boolean {
  for (const cat of FAQ_CATEGORIES) {
    for (const item of cat.items) {
      if (item.id === id) return true;
    }
  }
  return false;
}

export default memo(FAQPage);
