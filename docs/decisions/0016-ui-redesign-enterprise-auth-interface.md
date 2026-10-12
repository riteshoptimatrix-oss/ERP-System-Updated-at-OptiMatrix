# ADR 0016: UI Redesign - Ultra-Premium Off-White Enterprise Authentication Interface

## Status
Accepted

## Context
The original login interface utilized a dark background, navy login container, and bright saturated blue buttons. While functional, it lacked the refined, bespoke, and authoritative feel appropriate for a high-precision manufacturing enterprise producing industrial machinery across dual facilities (`Unit 1` and `Unit 2`).

## Decisions

### 1. Warm-Neutral & Off-White Design System
- Transitioned the entire color scheme to a Swiss editorial industrial aesthetic:
  - **Main background**: `#F7F6F2`
  - **Primary surface**: `#FFFFFF`
  - **Secondary surface**: `#F0EFE9`
  - **Main text**: `#202722`
  - **Secondary text**: `#73786F`
  - **Primary accent**: Deep forest green `#315C45` (hover: `#254936`, active: `#1E3B2C`)
  - **Borders**: Warm-neutral `#E6E4DC`
  - **Subtle highlight**: `#E8EEE7`
  - **Input background**: `#FBFBF8`
  - **Error state**: `#B42318`
- Integrated variables in `src/styles/globals.css` using Tailwind CSS V4 `@theme inline`.

### 2. Split-Screen Layout Composition
- **Left Panel (58% width on desktop)**:
  - Clean typographic wordmark with minimalist geometric industrial mark.
  - Active operational facility badges (`Unit 1 • Heavy Machining` and `Unit 2 • Assembly & QC`).
  - Large editorial serif headline: *"Precision in Production. Clarity in Every Operation."*
  - Refined technical grid and architectural layout showcasing three core capabilities: Integrated Manufacturing, Real-Time Inventory Visibility, and Unified Operations.
  - Discrete footer showing company copyright and version code.
- **Right Panel (42% width on desktop)**:
  - Perfectly centered authentication card on pure white surface (`#FFFFFF`).
  - Thin warm-neutral border (`#E6E4DC`) with soft, multi-layered elevation shadow (`shadow-card-elevated`).
  - Understated brand mark with "Welcome back" heading and supporting context.
  - Input fields with leading icons (`Mail`, `Lock`), password reveal toggle (`Eye`/`EyeOff`), and smooth focus rings.
  - Deep forest-green primary button (`#315C45`) with hover transitions, loading spinner, and disabled states.
  - Security notices and absence of exposed credentials.

### 3. Preserved Authentication Architecture
- Preserved single-login API integration (`/api/v1/auth/login`) with Argon2id verification and HttpOnly cookies.
- Preserved redirect parameters (`redirect=%2F...`) upon successful login.
- No dummy/mock bypasses; client talks directly to live FastAPI backend.

## Verification
- `npx tsc --noEmit` verified with 0 errors.
- `npm run build` compiled all 30 routes cleanly with 0 hydration errors.
- All backend authentication tests passed (`pytest tests/test_auth.py`).
