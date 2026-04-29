---
version: alpha
name: Mutation Lab v2.5.0
description: A high-fidelity, dark-mode research console design system for quantitative finance and algorithmic strategy mutation.
colors:
  bg-deep: "#09090b"
  bg-card: "#111114"
  bg-muted: "#18181b"
  border-dim: "#27272a"
  primary: "#8b5cf6"
  primary-dim: "#1e1b4b"
  win-green: "#10b981"
  lose-red: "#ef4444"
  baseline-blue: "#3b82f6"
  text-main: "#fafafa"
  text-muted: "#a1a1aa"
typography:
  display:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: -0.02em
  headline:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: 600
    lineHeight: 1.3
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: 700
    lineHeight: 1
    letterSpacing: 0.05em
  code:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.6
rounded:
  sm: 6px
  md: 12px
  lg: 18px
  full: 9999px
spacing:
  base: 16px
  xs: 4px
  sm: 8px
  md: 24px
  lg: 40px
  sidebar: 240px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.text-main}"
    rounded: "{rounded.sm}"
    typography: "{typography.body-md}"
  card-base:
    backgroundColor: "{colors.bg-card}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
  badge-win:
    backgroundColor: "rgba(16, 185, 129, 0.1)"
    textColor: "{colors.win-green}"
    rounded: "{rounded.sm}"
---

# DESIGN.md

## Overview
Mutation Lab is a **white-box first research console**. The brand personality is professional, institutional, and engineered. It avoids "gamified" elements in favor of high-density information, data transparency, and a "Glassmorphic Noir" aesthetic.

The UI should feel like a specialized cockpit for quant researchers. It utilizes a deep obsidian color palette to reduce eye strain during long sessions and uses high-contrast accents (Purple, Green, Blue) solely to indicate hierarchy and performance results.

## Colors
The palette is rooted in a "Deep Space" theme where depth is conveyed through subtle tonal Shifts rather than traditional lighting.

- **Primary Accent (#8b5cf6):** "Mutation Purple." Used for active navigational states, primary calls to action, and representing "Child" strategies.
- **Success Green (#10b981):** Used for "Win" verdicts, profitable equity curves, and promoted strategy leaders.
- **Error Red (#ef4444):** Used for "Lose" verdicts and drawdowns.
- **Baseline Blue (#3b82f6):** Specifically reserved for "Parent" or baseline strategies to distinguish them from mutations.
- **Neutral Grays:** We use a range of Zinc/Slate grays for text. Headlines are nearly pure white (#fafafa), while metadata uses a muted slate (#a1a1aa).

## Typography
The system uses **Inter** for all UI elements to maintain a modern, readable SaaS feel, and **JetBrains Mono** for all technical data, code blocks, and JSON payloads.

- **Display & Headlines:** Used for page titles and section headers. Should have tight letter spacing (-0.02em).
- **Labels (All Caps):** Used for small headers above metrics (e.g., "PROFIT FACTOR"). These are strictly uppercase with 0.05em letter spacing to evoke a technical, paged-data feel.
- **Technical Data:** All numbers, PnL values, and timestamps should ideally use a monospaced font or tabular numbers to ensure columns align in tables.

## Layout
The application follows a **Fixed-Sidebar Navigation** model.

- **Sidebar:** Fixed at 240px. Contains the brand mark, semantic nav groups (Overview, Research, Engine), and system health.
- **Main Canvas:** A fluid area with a maximum comfortable reading width. Internal sections are separated by 40px (spacing.lg).
- **The Tri-Grid:** Comparison views (Parent vs Candidate vs Best Child) are displayed in a 3-column grid with "VS" separators in between to emphasize the causal link between mutations.

## Elevation & Depth
Mutation Lab does not use drop shadows. Instead, it uses **Border-based Layering** and **Tonal Differentiation**.

1. **Level 0 (Background):** `#09090b` (The deepest layer).
2. **Level 1 (Cards/Containers):** `#111114` with a 1px border of `#27272a`.
3. **Level 2 (Active Elements):** `#18181b` (Used for hover states or nested inputs).

## Shapes
The shape language is **Architectural**. 
- Standard buttons and badges use a 6px radius (sm).
- Component cards use a 12px radius (md) for a balanced look.
- Large hero elements or the sidebar use an 18px radius (lg) on specific corners to create a "contained" cockpit feeling.

## Components

### Comparison Cards
These are the core of the Research UI. Each card must have a 2px colored "Top Border" or "Accent Bar" that identifies the strategy role:
- **Parent:** Blue
- **Candidate:** Purple
- **Best Child:** Green

### Evidence Ledger (Table)
Tables are high-density. 
- **Headers:** Muted text, font-size 12px.
- **Rows:** 1px bottom border. Hover state should subtly lighten the background.
- **Badges:** Verdicts (Win/Lose) must be clearly badged with low-opacity background fills.

### Code Editor
Used for baseline registration. 
- Background: `#0d0d0f`.
- Include line numbers in a muted color.
- Syntax highlighting should follow a "One Dark" or similar professional theme.

## Do's and Don'ts

### Do
- Use monospaced fonts for PnL and technical metrics.
- Keep the "Evidence Ledger" as the primary source of truth (high density).
- Use the 1px `#27272a` border to separate all major containers.
- Align "VS" indicators perfectly between comparison cards.

### Don't
- Do not use vibrant gradients for backgrounds; keep them solid or very subtle radials.
- Do not use rounded corners on internal table cells.
- Do not use "Mutation Purple" for success/profit messages (use Green).
- Do not use more than one primary button per view.

## Consumer Guidance for LLMs
When generating new views based on this system:
1. Always start with the `#09090b` background.
2. Group related items into cards (`#111114`).
3. If the data is a metric (like Profit Factor), make it bold and large.
4. If the data is secondary (like a Run ID), make it small, muted, and monospaced.
5. Use `8b5cf6` (Purple) as the default "Action" color unless the action is "Promote" or "Success," in which case use `10b981` (Green).