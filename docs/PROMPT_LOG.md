# AeroFly — Prompt Log

Persistent audit trail of all user requests. Each entry documents a user prompt with timestamp, branch, and verbatim text.

---

### 2026-04-07 23:00 — Initial project setup and scaffolding (`main`)

> I want you to look up the setup and organisation of CPGrid-Bot which has a very nice and comprehensive claude.md file. Use the conventions from this claude.md. We should take over from this file all what is relevant for us. We will build a new and separate Design Kit especially for this project. Have a look also on the folder structure. e.g. the report folder shall also exist for the reports which we will create during development. In general analyze the cpgrid-bot and use the best out of it. AeroFly is in the first phase a compendium of all aerodrom maps and informations which a pilot needs to start from an airport or to land at an airport in germany. We will index, search and interprete all available information from basically as a primary source DSF (Deutsche Flugsicherung). We will make this information available to other tools which we plan to build via API access. So we will need also a swagger. We will need a performant db. All the components will be build in dedicated containers and the fapplication will run in a docker. The language shall be german and english. It is also planned to have later on an offline app version for ios and android. but this will be maybe phase 2 or even 3. The whole project must be setup by you on github. Also all the rules how we use github should be described in the claude.md from cpgrid-bot.

### 2026-04-19 — Build complete design kit based on Gemini kit (`feat/2-design-kit-v2`)

> C:\Users\DoronMarcu\source\repos\AeroFly\docs\Design-Kits\gemini-design-kit.html Entwickel auf der Basis dieses Design Kits von Gemini das komplette Design Kit, so wie wir es dann brauchen, mit allen Komponenten für unsere Weiterentwicklung.

### 2026-04-19 — Confirm design kit intake choices (`feat/2-design-kit-v2`)

> 1b; 2a; 3a; 4a; 5a; 6a; 7h

### 2026-04-19 — Run housekeeping workflow (`feat/2-design-kit-v2`)

> do housekeeping

### 2026-04-19 — Start Phase 1 (scope selection) (`develop`)

> start with phase 1

### 2026-04-19 — Phase 1 start choices (DB schema + all options, open issue) (`develop`)

> 1a; 2d; 3a

### 2026-04-19 — Schema design decisions (ICAO PK, coords phased, bilingual cols, charts in scope, ICAO NOTAM, per-service schemas, smoke test) (`feat/4-db-schema-foundation`)

> 1a; 2c; 3a; 4a; 5c; 6b; 7a

### 2026-04-19 — Run housekeeping after schema work (`feat/4-db-schema-foundation`)

> do housekeeping

### 2026-04-19 — Make the stack runnable end-to-end (`develop`)

> build docker and perform all end-to-end testing and do everything so that I can run it.

### 2026-04-19 — Run housekeeping after making stack runnable (`chore/6-runnable-dev-env`)

> do housekeeping

### 2026-04-19 — Question: is the empty frontend expected? (`develop`)

> [screenshot: plain page with "AeroFly" heading + one subtitle line] Das ist alles, was ich sehe. Mehr sehe ich nicht, wenn ich das Frontend aufmache. Ist das so richtig? Hast du dir das so gedacht oder sollte da mehr angezeigt werden?

### 2026-04-19 — Pick option C (vertical slice) (`develop`)

> C

### 2026-04-19 — Vertical slice choices: `/aerodromes` prefix, limit/offset, Dashboard landing, real seed data, full DE/EN (`develop`)

> 1a; 2a; 3b; 4c; 5b

### 2026-04-19 — Load already-scraped data into Docker, not demo seeds (`feat/8-aerodrome-listing`)

> Wir haben schon alle Daten von den Flughäfen gescreate. Die solltest du alle lokal in deinem Docker auch zur Verfügung haben. Und das Scraten sollte nur dafür notwendig sein, wenn Updates verfügbar sind, die eben abzudaten.

### 2026-04-19 — Run housekeeping after vertical slice + import (`feat/8-aerodrome-listing`)

> do housepeeping

### 2026-04-19 — Create 6 GitHub issues + start implementation (`develop`)

> Mach ein GitHub-Issue aus: "DFS HTML/chart parser (extract structured runways/frequencies/coords from the existing scraped images) ·  Meilisearch sync · NOTAM integration · chart image display in detail view · authentication · responsive/mobile layout." - Und starte mit der Implementierung in einem neuen Branch.

### 2026-04-19 — Reframe: no auth, charts are the product, close #10 and #14 (`feat/13-chart-image-display`)

> es gibt keine authentifizierung für die bilder und informationen. du kommst ohne login überall hin und die bilder die wir bereits gescraped haben sollten eigentlich völlig ausreichend sein. mehr informationen als wir schon haben gibt es nicht

### 2026-04-19 — Run housekeeping after chart display (`feat/13-chart-image-display`)

> do housekeeping

### 2026-04-19 — Chart click-to-enlarge + zoom (`develop`)

> Ich brauche für die Bilder Click & Large mit Zoom-Funktionalität.

### 2026-04-19 — Chart viewer should open fit-to-screen (`feat/17-chart-zoom-viewer`)

> Nach dem Click Enlarge soll das erste Bild, also die Einstellung, immer ein Fit Image sein, also so, dass das ganze Bild in den Ausschnitt passt.

### 2026-04-19 — Run housekeeping after chart viewer (`feat/17-chart-zoom-viewer`)

> do housekeeping

### 2026-04-19 — Design & plan: chart thumbnail grid (`develop`)

> Handle as a team consisting of: Software Architect / Product Manager / UX / Airline Pilot / ATC / Aviation Safety Expert / AI Engineer. I want you to Design & Plan following feature: thumbnails instead of extendable lines. In der Detailübersichtseite eines Flughafens, zum Beispiel EDNY Friedrichshafen, haben wir unter dem Menüpunkt Karten Expendables Lines … statt diesen Expendable Lines möchte ich einfach die Thumbnails haben, so dass man sofort sieht, was hinter der einzelnen Bezeichnung ist … 10 iterations, HTML report, no implementation until GO.

### 2026-04-19 — GO — implement chart thumbnail grid per plan (`develop`)

> go

### 2026-04-19 — Add favicon for browser tabs (`develop`)

> Gebe der App ein schönes Favikon Vor allem für die Browser-Tabs.

### 2026-04-19 — Proposal: extract structured info from scraped charts (OCR/parser) (`develop`)

> ok - wie gest es mit dem erkennen der notwendigen informationen wie z.B. frequenzen, pisten, elevation, datum der info und anderes sowie das ocr oder chart parser. mache mir einen vorschlag dazu. noch keine implementierung. berate dich mit deinem team bestehend aus: Software Architect / Product Manager / UX / Airline Pilot / ATC / Aviation Safety Expert / AI/Prompt Engineer

### 2026-04-19 — Rock-solid plan with 20 iterations + interactive HTML (`develop`)

> ich brauche von dir lösungen, damit alles rock-solid ist. keine risiken - hier geht es um leben und tod. führt mindestens 20 iterationen des gleichen brainstormings vor und challenged die möglichkeiten. ich brauche alle informationen aber absolut zuverlässig. … ich hätte den plan gerne auch als interaktives HTML …

### 2026-04-20 — GO komplett — alle 9 Phasen, Safety-Gate vor GA (`develop`)

> 3

### 2026-04-20 19:45 — Weiter after compact (`develop`)

> weiter

### 2026-04-20 19:55 — Clarify branch/sections/image-guard; restate on-demand rule (`develop`)

> 1 - i dont understand - clarify; 2 thats fine; 3 clarify - not clear for me; 4 4 use as stored; 5 finish scraper first. / in general i want the information scraped and read from claude and openai always only on user request. not all just on storage. and if work is done everything/all outputs shall be stored. update always only on user request per aerodrom

### 2026-04-20 20:00 — Confirm: 1b; sections 2.2/2.12/2.13/2.18/2.20; 4a retry on fail (`develop`)

> 1b; 3 add the 4 and add also 2.20; 4 a and if it fails beacause to large shrink it and retry

### 2026-04-20 20:10 — VFR focus; IFR nice-to-have; free hand on issue scope (`develop`)

> 1 i am focused on all vfr relevant information. if you get additional ifr information its good but not Absolutely Necessary. 2 Just focus on VFR. 3 You can decide yourself.

### 2026-04-20 20:55 — Continue / run housekeeping for #29 (`feat/29-scraper-per-icao-chart-types`)

> continue
