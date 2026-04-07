# AeroFly — Prompt Log

Persistent audit trail of all user requests. Each entry documents a user prompt with timestamp, branch, and verbatim text.

---

### 2026-04-07 23:00 — Initial project setup and scaffolding (`main`)

> I want you to look up the setup and organisation of CPGrid-Bot which has a very nice and comprehensive claude.md file. Use the conventions from this claude.md. We should take over from this file all what is relevant for us. We will build a new and separate Design Kit especially for this project. Have a look also on the folder structure. e.g. the report folder shall also exist for the reports which we will create during development. In general analyze the cpgrid-bot and use the best out of it. AeroFly is in the first phase a compendium of all aerodrom maps and informations which a pilot needs to start from an airport or to land at an airport in germany. We will index, search and interprete all available information from basically as a primary source DSF (Deutsche Flugsicherung). We will make this information available to other tools which we plan to build via API access. So we will need also a swagger. We will need a performant db. All the components will be build in dedicated containers and the fapplication will run in a docker. The language shall be german and english. It is also planned to have later on an offline app version for ios and android. but this will be maybe phase 2 or even 3. The whole project must be setup by you on github. Also all the rules how we use github should be described in the claude.md from cpgrid-bot.
