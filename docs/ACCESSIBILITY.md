# Accessibility

- A first-position skip link leads to the main landmark, which remains available while a route loads. Pages use a top-level heading, update the document title, and move focus to the heading as the route renders.
- The availability grid has one tab stop. Arrow keys move between cells, Page Up and Page Down move between days, and Home and End move within the day. Enter or Space selects a slot. Shift with Up or Down extends a selection, and Escape clears it. Unavailable cells can be inspected while navigating and cannot be selected.
- Every calendar cell has a screen-reader name. The grid also has a list view with native buttons for available times and a live status for the selected interval.
- Form controls have visible labels. Field validation marks the affected control as invalid and links it to its explanatory message.
- Statuses have text labels and messages use alert or status regions. Native dialogs have accessible titles and return focus to the control that opened them.
- Light and dark themes have tested colour token pairs. Reduced-motion preferences disable transitions and animations. The app defines a visible keyboard focus outline.
- Utilisation and busiest-time charts have table toggles for access to the underlying data.

The frontend suite includes axe checks for sign-in, the availability grid, and the conflict recommendation view, plus 28 WCAG contrast assertions for light and dark themes.
