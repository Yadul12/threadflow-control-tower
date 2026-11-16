# THREADFLOW — Figma Enterprise Design System & UI Handoff Package

**Design Direction:** Purposeful Retail & Supply Chain Operations Control Tower  
**Figma Integration Disclosure:** Live Figma API write credentials are not connected in this environment. This handoff package provides the complete **Design Tokens JSON (`design_tokens.json`)**, **Component Specifications**, **Interaction States**, and **SVG Wireframe & Component Boards (`assets/*.svg`)** ready for direct import into Figma.

---

## 1. Visual Direction & Strict Anti-Patterns

### 1.1 Enterprise Visual Principles
- **Information-Dense Operational Surfaces:** High data-to-ink ratio tailored for category managers, procurement specialists, inventory planners, and warehouse leads working on 1440px–1920px desktop monitors and 1024px warehouse tablets.
- **Warm Neutral Canvas & High-Contrast Charcoal Typography:**
  - App Background: Warm Alabaster Stone (`#F6F5F2`)
  - Muted Secondary Header Surface: Warm Grey (`#EFECE6`)
  - Primary Table & Card Surface: Crisp White (`#FFFFFF`) with 1px structural borders (`#D6D3CD`)
  - Primary Typography: Deep Charcoal (`#18181B`), Secondary Slate (`#3F3F46`), Muted Caption (`#71717A`)
- **Tabular Monospace Numerals:** Every SKU code, PO number, AWB, quantity, INR currency column, lead-time figure, and SLA timer uses `JetBrains Mono` (`font-mono tabular-nums`) with strict right-alignment for numeric columns and left-alignment for text/identifiers.
- **Restrained Semantic Status Tokens:**
  - **Operational Healthy / SLA Met / QC Passed:** Deep Forest Green (`#166534` text on `#DCFCE7` badge fill, `#86EFAC` border)
  - **Active Workflow / In-Transit / Acknowledged:** Industrial Navy (`#1E3A8A` text on `#DBEAFE` fill, `#93C5FD` border)
  - **Warning / Low Stock / Partial GRN / Elevated Backlog:** Muted Ochre Amber (`#9A3412` text on `#FFEDD5` fill, `#FDBA74` border)
  - **Critical Breach / Stockout / Delayed PO / QC Failed:** Crimson Brick (`#991B1B` text on `#FEE2E2` fill, `#FCA5A5` border)

### 1.2 Strictly Prohibited Visual Elements (Enforced)
- Zero purple-blue gradients or neon AI glows
- Zero glassmorphism (`backdrop-blur` cards) or floating decorative blobs
- Zero oversized marketing hero banners
- Zero repeated identical KPI card strips on every sub-page
- Zero decorative emojis or unaligned table columns

---

## 2. Reusable Component Library & Interaction States

1. **`OperationalDataGrid`:**
   - Sticky 36px uppercase column header (`bg-[#EFECE6] text-[#3F3F46] text-[11px] font-semibold tracking-wider uppercase border-b border-[#D6D3CD]`).
   - 42px compact row height with `hover:bg-[#F6F5F2]` highlight and inline row action triggers.
   - Built-in states: `LoadingSkeleton`, `EmptyFilterState` (with one-click filter reset), `ValidationErrorBanner`, `ConfirmationModal`, and `ActionToast`.
2. **`StatusBadge`:**
   - Squared-off `rounded-sm px-2 py-0.5 text-[11px] font-mono font-medium border` indicator mapping 32 operational states across Inbound, Inventory, and Outbound.
3. **`SplitInspectorDrawer`:**
   - Slide-over or inline expansion panel displaying PO line items, Supplier issue logs, Shipment 5-step tracking timelines, or Evidence-Grounded GenAI analysis.
