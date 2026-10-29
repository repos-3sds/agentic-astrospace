Status: canonical — the Siddha wordmark and where its copies live.

`ui/public/brand/siddha-wordmark.svg` (354 x 111) is the Siddha wordmark, supplied by Hawk on
2026-10-29 as `Siddha_Original.svg`. It replaced the Samarkan font, which is
shareware for personal use only and must not come back.

Every copy uses the same paths:

| Where | File | How it takes colour |
| --- | --- | --- |
| App (web and native) | `ui/public/brand/siddha-wordmark.svg`, served at `/brand/siddha-wordmark.svg` | CSS mask on `.siddha-brand` / `.siddha-wordmark` (`src/styles.scss`), filled with the element's text colour |
| Share image | `wordmark.ts` (this folder) | canvas `Path2D`, colour passed in |
| Android widget | `android/app/src/main/res/drawable/widget_wordmark.xml` | fill colour in the drawable |
| Website | `firebase-public/brand/siddha-wordmark.svg` | the same CSS mask, inline in each page |
| Email logo | `ui/public/email/siddha-logo.png` (and `firebase-public/`) | rendered once, rust |

The wordmark is sized in em: 2.8em wide, the width the old typeset wordmark had
at the same font size. If the drawing changes, update every row above.
