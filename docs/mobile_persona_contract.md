# Mobile persona presentation contract

AstroSpace has one calculation engine and three presentation modes. A user can
change mode without changing their chart, calendar, compatibility score,
periods, transit data, or saved readings.

| Slice | Guided | Balanced | Practitioner | Owner |
| --- | --- | --- | --- | --- |
| Entry and first insight | Plain-language meaning and one action | Personal summary plus chart preview | Computed chart, conventions, and workbench entry | Frontend presentation |
| Primary navigation | Today, Ask, remedies, Calendar | Today, Ask, Chart, Calendar | Today, Chart, Periods, Transits | Frontend presentation |
| Today and explanation | Meaning first; technical grids hidden | Meaning plus expandable evidence | Technical basis and conventions inline | Shared API truth; frontend disclosure |
| Ask answer | Verdict and next action | Verdict, reasoning, and evidence sheet | Evidence and conventions inline | Shared API truth; frontend disclosure |
| Chart and periods | Story-led topics and plain period language | Standard chart hub and period hierarchy | Workbench, exact degrees, convention labels, deeper hierarchy | Shared API truth; frontend disclosure |
| Calendar and compatibility | Key dates and headline result | Standard calendar and koota summary | Calculation convention and complete koota breakdown | Shared API truth; frontend disclosure |
| Notifications and errors | Actionable alerts; gentle recovery | Standard alert stream and recovery | Transit alerts plus diagnostic detail | Frontend filtering and framing |

`experience_mode` and `tone` are persisted locally for immediate startup and in
`/api/v1/settings` for account continuity. Tone changes wording and recovery
framing only; it must never change calculated facts.

## Acceptance stories

- Guided: register, enter birth details, see a simple first insight, continue to
  Today, ask a question, follow a suggested action, then sign out.
- Balanced: register, enter birth details, see the personal summary, explore the
  chart and evidence behind Today, use Calendar or Compatibility, then sign out.
- Practitioner: register, enter birth details, confirm chart conventions, move
  between Chart, Periods, and Transits, inspect full evidence, then sign out.

The Playwright persona contract covers the mode-specific first insight, primary
navigation, and the shared empty-profile boundary at 375×812. The account
lifecycle test covers the registration-to-first-insight transition and logout.
