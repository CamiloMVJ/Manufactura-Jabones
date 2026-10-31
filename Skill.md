# ERP UI/UX — Professional Modern Design Skill

## Objective
Transform the ERP into a polished, modern, professional enterprise application while preserving all existing functionality, business logic, routes, Livewire behavior, database structure, permissions and workflows.

The interface must feel like a real production ERP, not a school project or generic admin template.

## Visual Direction
Use a clean enterprise SaaS aesthetic inspired by modern ERP, CRM and operations platforms.

- Minimal, elegant and information-dense without feeling crowded.
- Light neutral backgrounds with white surfaces/cards.
- Strong visual hierarchy.
- Consistent spacing, typography, borders and component sizes.
- Subtle shadows only where useful.
- Rounded corners between 10–14px.
- Avoid excessive gradients, neon colors, oversized cards or decorative effects.
- Use one coherent primary color with semantic colors for success, warning, danger and information.
- Maintain excellent contrast and readability.

## Navigation
Create a professional application shell:

- Collapsible sidebar with logo, grouped modules and clear active states.
- Use meaningful icons for every module and important action.
- Do not use emojis as interface icons.
- Use Lucide, Heroicons or an equivalent professional icon library.
- Top bar should contain page context, search when useful, notifications and user/profile controls.
- Breadcrumbs for deeper pages.
- Navigation must remain consistent throughout the entire ERP.

## Dashboard
The dashboard should immediately communicate system status.

Use:
- KPI cards with icon, value, label and optional trend.
- Charts only when they provide meaningful information.
- Recent activity.
- Alerts and pending actions.
- Inventory / production / purchasing / sales summaries.
- Clear visual separation between operational information.

Avoid filling the screen with unnecessary cards.

## Tables
Tables are one of the most important ERP components.

Make them professional and highly usable:

- Clear header.
- Comfortable but compact row height.
- Search.
- Filters.
- Sorting.
- Pagination.
- Status badges.
- Contextual action menu using icons.
- Row hover state.
- Empty states.
- Responsive behavior.
- Sticky headers when useful.

Never overcrowd rows with many large buttons.

Use an action dropdown or compact icon buttons for View, Edit, Delete and additional actions.

## Forms
Forms must be clean and structured.

- Group related fields into sections.
- Visible labels above fields.
- Clear required indicators.
- Useful placeholder/helper text.
- Consistent input heights.
- Inline validation.
- Professional select/date/file controls.
- Primary action clearly distinguished from secondary actions.
- Prevent unnecessarily long single-column forms on desktop.
- Use responsive 2-column layouts when appropriate.

## Status and Feedback
Every action must provide clear feedback.

Include:
- Loading states.
- Skeletons where appropriate.
- Success/error notifications.
- Confirmation dialogs for destructive actions.
- Disabled states.
- Empty states.
- Helpful validation messages.

Never allow buttons to appear unresponsive.

## Manufacturing / ERP Experience
Pay special attention to:

- Products
- BOM
- Production orders
- Purchase orders
- Material reception
- Inventory movements
- Lots
- Quality control
- Sales / dispatch
- Suppliers
- Customers
- Reports
- KPI dashboards

The user must clearly understand the transactional flow:

Purchase → Reception → Production → Inventory → Sale/Dispatch.

Use statuses, progress indicators, timelines and contextual information where they improve understanding.

Lot traceability and quality records must be visually easy to follow.

## KPI Presentation
Design reusable KPI components for indicators such as:

- OEE
- Yield
- Inventory turnover
- Unit cost
- Cycle time
- Production efficiency
- Rejection / scrap rate

Each KPI should show:
- Name
- Current value
- Unit
- Context or comparison when available
- Simple visualization only when useful

## Responsive Design
Desktop is the primary ERP workspace, but every page must remain usable on tablet and mobile.

- Sidebar becomes drawer/hamburger navigation.
- Tables adapt intelligently instead of simply shrinking.
- Forms become single-column.
- Actions remain easy to tap.
- No horizontal overflow unless unavoidable for complex data grids.

## Design Consistency
Create or reuse centralized design tokens/components for:

- Colors
- Typography
- Spacing
- Buttons
- Inputs
- Cards
- Tables
- Badges
- Alerts
- Modals
- Dropdowns
- Tooltips
- Pagination
- Empty states
- Icons

Do not create a different visual style for every module.

## Implementation Rule
Before modifying a page:
1. Inspect its existing logic.
2. Preserve all functionality.
3. Improve layout and hierarchy.
4. Reuse existing components when possible.
5. Refactor duplicated UI into reusable components.
6. Verify desktop and mobile views.
7. Verify hover, focus, loading, empty, success and error states.

Never remove functional features merely to simplify the design.

The final result should look like a coherent, premium ERP product ready to be demonstrated to a company or evaluated professionally.
