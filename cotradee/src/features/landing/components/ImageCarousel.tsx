import { useState, useEffect, useCallback } from 'react';

/**
 * Dashboard image carousel with vertical slide-through animation.
 *
 * Behavior: Image slides up from bottom → stays visible ~1.5s →
 * slides out through top → next image slides up from bottom.
 * Loops automatically and continuously.
 *
 * Replace the placeholder cards with real dashboard screenshots by
 * populating the `images` array with actual image paths.
 */

// ── Replace these with real dashboard screenshot paths ───────────────────
// e.g. '/assets/landing/dashboard-1.png'
const SLIDES = [
  {
    id: 1,
    label: 'AI-Powered Analysis',
    gradient: 'linear-gradient(135deg, #0a1a0a 0%, #0d2b0d 40%, #0a0f0a 100%)',
    description: 'Multi-timeframe chart analysis with AI confidence scoring',
  },
  {
    id: 2,
    label: 'Trade Execution',
    gradient: 'linear-gradient(135deg, #0a0a1a 0%, #0d0d2b 40%, #0a0a0f 100%)',
    description: 'One-click execution with automated risk management',
  },
  {
    id: 3,
    label: 'Portfolio Analytics',
    gradient: 'linear-gradient(135deg, #1a0a0a 0%, #2b0d0d 40%, #0f0a0a 100%)',
    description: 'Real-time P&L tracking and performance metrics',
  },
  {
    id: 4,
    label: 'Risk Management',
    gradient: 'linear-gradient(135deg, #0a1a1a 0%, #0d2b2b 40%, #0a0f0f 100%)',
    description: 'Dynamic position sizing with drawdown protection',
  },
  {
    id: 5,
    label: 'Trade Journal',
    gradient: 'linear-gradient(135deg, #1a1a0a 0%, #2b2b0d 40%, #0f0f0a 100%)',
    description: 'Automated journaling with win-rate analytics',
  },
  {
    id: 6,
    label: 'Smart Alerts',
    gradient: 'linear-gradient(135deg, #0a0a0a 0%, #1a2b0d 40%, #0a0f0a 100%)',
    description: 'Real-time notifications for trade setups and events',
  },
];

const DISPLAY_DURATION = 1800; // ms image stays visible
const ENTER_DURATION = 600;   // ms for slide-in animation
const EXIT_DURATION = 500;    // ms for slide-out animation

type SlideState = 'hidden' | 'entering' | 'active' | 'exiting';

export default function ImageCarousel() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [slideState, setSlideState] = useState<SlideState>('entering');

  const advanceSlide = useCallback(() => {
    // Start exit animation
    setSlideState('exiting');

    setTimeout(() => {
      // Move to next slide
      setCurrentIndex((prev) => (prev + 1) % SLIDES.length);
      setSlideState('entering');

      // After enter animation completes, set to active
      setTimeout(() => {
        setSlideState('active');
      }, ENTER_DURATION);
    }, EXIT_DURATION);
  }, []);

  useEffect(() => {
    // Initial entry: after enter animation, set active
    const initialTimer = setTimeout(() => {
      setSlideState('active');
    }, ENTER_DURATION);

    return () => clearTimeout(initialTimer);
  }, []);

  useEffect(() => {
    if (slideState !== 'active') return;

    const timer = setTimeout(advanceSlide, DISPLAY_DURATION);
    return () => clearTimeout(timer);
  }, [slideState, advanceSlide]);

  const slide = SLIDES[currentIndex];

  return (
    <div className="carousel-viewport mx-auto">
      {/* Active slide */}
      <div
        key={slide.id}
        className={`carousel-slide ${slideState}`}
      >
        {/* Placeholder dashboard visual — replace with <img> when ready */}
        <div
          className="dashboard-placeholder"
          style={{ background: slide.gradient }}
        >
          {/* Simulated dashboard UI elements */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
              <div className="w-3 h-3 rounded-full bg-[#febc2e]" />
              <div className="w-3 h-3 rounded-full bg-[#28c840]" />
            </div>
            <div className="flex gap-2">
              <div className="h-2 w-16 rounded bg-white/[0.06]" />
              <div className="h-2 w-20 rounded bg-white/[0.06]" />
            </div>
          </div>

          {/* Simulated sidebar + main content area */}
          <div className="flex gap-4 flex-1">
            {/* Sidebar */}
            <div className="w-14 flex-shrink-0 flex flex-col gap-3 pt-4">
              {[...Array(5)].map((_, i) => (
                <div
                  key={i}
                  className="w-8 h-8 rounded-lg mx-auto"
                  style={{
                    background: i === 0
                      ? 'rgba(118, 185, 0, 0.20)'
                      : 'rgba(255, 255, 255, 0.04)',
                  }}
                />
              ))}
            </div>

            {/* Main content */}
            <div className="flex-1 flex flex-col gap-3">
              {/* Top bar */}
              <div className="flex gap-3">
                <div className="h-6 flex-1 rounded bg-white/[0.04]" />
                <div className="h-6 w-24 rounded bg-[#76B900]/20 flex items-center justify-center">
                  <span className="text-[0.5rem] text-[#76B900] font-semibold">
                    {slide.label}
                  </span>
                </div>
              </div>

              {/* Chart area */}
              <div className="flex-1 rounded-lg bg-white/[0.02] border border-white/[0.04] flex items-end p-4 gap-1">
                {[...Array(24)].map((_, i) => {
                  const h = 20 + Math.sin(i * 0.5 + slide.id) * 30 + Math.random() * 20;
                  return (
                    <div
                      key={i}
                      className="flex-1 rounded-t"
                      style={{
                        height: `${h}%`,
                        background: h > 50
                          ? 'rgba(118, 185, 0, 0.35)'
                          : 'rgba(255, 80, 80, 0.25)',
                      }}
                    />
                  );
                })}
              </div>

              {/* Bottom stats row */}
              <div className="flex gap-3">
                {[...Array(3)].map((_, i) => (
                  <div
                    key={i}
                    className="flex-1 h-14 rounded-lg bg-white/[0.03] border border-white/[0.04]"
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Slide indicator dots */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2 z-10">
        {SLIDES.map((s, i) => (
          <div
            key={s.id}
            className="w-1.5 h-1.5 rounded-full transition-all duration-300"
            style={{
              background:
                i === currentIndex
                  ? '#76B900'
                  : 'rgba(255, 255, 255, 0.20)',
              transform: i === currentIndex ? 'scale(1.4)' : 'scale(1)',
            }}
          />
        ))}
      </div>
    </div>
  );
}
