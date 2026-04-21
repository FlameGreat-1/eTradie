# Frontend Architecture & Modular Integration Plan

This plan completely restructures the `cotradee` React application away from Next.js over to **Vite 5.4 + React 18** using an Enterprise-Grade **Feature-Based Architecture**.

## Design Philosophy

- **Feature-Sliced Architecture:** We group files by domain/feature (e.g., `auth`, `analysis`, `broker`) rather than function (e.g., all `components/` in one folder). This prevents chaotic file bloat and naturally enforces a <200 lines per-file hard limit.
- **Strict Separation of Concerns:**
  - UI logic goes into functional components.
  - State logic goes into Custom Hooks (`use...`).
  - Server communication goes strictly into TanStack `useQuery`/`useMutation` isolated under `api/` folders.
  - Auth Token cycling goes into an Axios interceptor `lib/axios.ts`.
- **Naming Conventions:** All component, hook, and API definition files will use strict `camelCase` naming conventions (e.g., `analysisFeed.tsx`, `latestAnalysis.ts`).
- **Assets Retention:** We will keep the custom icons/SVG assets in `/public` to ensure the Sidebar and branding remain exactly as beautiful and customized as they are currently. We will integrate `shadcn/ui` for standardized inputs, dialogs, and tables to speed up and clean up generic elements.

## Proposed Directory Structure (`src/`)

```bash
src/
├── assets/                  # CSS tokens, remaining theme files
│   └── index.css            # Tailwind directives, CSS variables
├── components/              # Global, dumb presentation components
│   ├── ui/                  # shadcn/ui integrated base elements
│   ├── layout/              # App Shell, Sidebar (using existing custom assets), Header
│   └── error/               # Global ErrorBoundary, 404 pages
├── config/                  # Environment variables, query client configs
├── features/                # Domain Logic — The Core of the App
│   ├── auth/                # Login, Token Refresh, Profile forms
│   ├── admin/               # User management, System global LLM configs
│   ├── alerts/              # WebSockets, Toast alerts, Event catch-up logs
│   ├── analysis/            # Run cycle buttons, feed, history, trade detailed modals
│   ├── broker/              # MT5 & MetaAPI connections, health pinging
│   ├── execution/           # Risk toggles, max limits, state tables 
│   ├── journal/             # Historical charts, metrics grid, realized PnL rows
│   ├── llm/                 # Manage AI API keys
│   ├── symbols/             # Pairs selection, system toggle resets
│   └── system/              # Run Intervals, master switch toggles
├── hooks/                   # Generic hooks: useDebounce.ts, usePersistState.ts
├── lib/                     # 3rd-party wraps: axios.ts (interceptors), obfuscation.ts
├── providers/               # Global wrappers (AppProvider, ReactQuery, AuthContext)
├── routes/                  # React Router lazy-loaded definitions
├── types/                   # Cross-feature interface mappings, enums
├── utils/                   # Pure functions (formatters, date math)
├── App.tsx                  # Root wrapper mapping router inside provider chains
└── main.tsx                 # Bootstraps the generic entry point
```

## Internal Feature Module Structure Example

Inside any `src/features/[featureName]`, we will enforce this schema:

```bash
src/features/analysis/
├── api/
│   ├── latestAnalysis.ts      # TanStack wrapper for GET /api/analysis/latest
│   ├── historyAnalysis.ts     # TanStack wrapper for GET /api/analysis/history
│   └── rerunAnalysis.ts       # TanStack wrapper for POST /api/analysis/rerun
├── components/
│   ├── analysisFeed.tsx       # Maps over the feed API
│   ├── historyTable.tsx       # < 150 lines, isolates the layout
│   └── tradeDetailModal.tsx   # Renders the exact plan reasoning from LLM
├── types/
│   └── index.ts               # Interfaces matching engine/gateway responses
└── index.ts                   # Public Export API
```

## Phase 1: Cleaning & Bootstrapping

1. **Delete Bad Paradigms:** Remove `next.config.ts`, `middleware.ts`, `.next/`, `components.json`, and all placeholder files.
2. **Setup Vite & TypeScript:** Scaffold Vite's SPA entrypoint (`index.html` at root), configure `vite.config.ts` path aliases (`@/*`), and set up dependencies like `axios`, `@tanstack/react-query`, `react-router-dom`.
3. **Establish Design System:** Retain custom assets in `/public/`. Map Tailwind custom properties correctly so the beautiful Sidebar stays preserved but integrated with `shadcn/ui`.
4. **Scaffold the Network Layer (`lib/axios.ts`):** Create the Auth token interceptor.

## Phase 2: Domain Implementation (Mapping to AUDIT.md)

1. **Auth & Application Shell:** Implement dynamic routing matching the original Sidebar layout.
2. **Dashboard Overview:** Setup Active symbols limits and the Run Cycle execution buttons.
3. **Admin & Integrations:** Connect the `llm` and `broker` features to their endpoints.
4. **Observability Panels:** Execute WebSockets configuration in `features/alerts`.
