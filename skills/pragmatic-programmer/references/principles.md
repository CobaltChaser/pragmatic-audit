# Principles reference

One-line paraphrases of the 100 tips from *The Pragmatic Programmer, 20th Anniversary Edition* by David Thomas and Andrew Hunt. These are original summaries, not quotations. Tip numbers follow that edition.

**Mode:** `auto` means a scanner rule checks part of it; `agent` means an agent can review it in context; `human` means it is a team or product decision.

| Tip | Paraphrase | Mode | Rule |
|---|---|---|---|
| 1 | Take pride in the craft; care whether the work is good. | human | |
| 2 | Think deliberately instead of working on autopilot. | agent | |
| 3 | You can change your situation; you are not a passive victim of it. | human | |
| 4 | Offer options instead of excuses. | human | |
| 5 | Fix small defects before they teach the team that neglect is normal. | auto | `PP-BROKEN-WINDOWS` |
| 6 | Create change by making a small part of the future work now. | human | |
| 7 | Keep the wider goal in view while working in the details. | agent | |
| 8 | Agree what quality means for this project and these users. | human | |
| 9 | Invest regularly in learning and broaden your range. | human | |
| 10 | Test advice and hype against your own context. | human | |
| 11 | Write requirements and documentation with the care you give code. | agent | `PP-DOCS` |
| 12 | Communication is part of the work, not a layer on top. | human | |
| 13 | Keep documentation close to the code it describes. | auto | `PP-DOCS`, `PP-COMMENTS` |
| 14 | Good design is measured by how cheaply it can change. | auto | `PP-COMPLEXITY` |
| 15 | Give every piece of knowledge one authoritative representation. | auto | `PP-DRY` |
| 16 | Make reuse easier than rewriting. | agent | |
| 17 | Separate concerns so unrelated changes do not collide. | auto | `PP-ORTHO` |
| 18 | Avoid irreversible decisions without evidence. | auto | `PP-REVERSIBILITY` |
| 19 | Choose fundamentals over fashion. | human | |
| 20 | Use a thin end-to-end path to prove the architecture. | auto | `PP-E2E` |
| 21 | Prototype to learn, then discard the prototype. | agent | |
| 22 | Program in the language of the problem domain. | agent | domain language |
| 23 | Estimate to expose what you do not understand. | human | |
| 24 | Refine the plan with what implementation teaches you. | human | |
| 25 | Prefer durable, plain-text formats for durable knowledge. | agent | |
| 26 | Use the shell to compose tools and automate routine work. | agent | |
| 27 | Learn your editor well enough that it stops interrupting thought. | human | |
| 28 | Put everything under version control. | auto | `PP-VCS` |
| 29 | Fix the problem, not the person. | human | |
| 30 | Stay calm when debugging; panic narrows the search. | human | |
| 31 | Reproduce a bug with a failing test before fixing it. | agent | `PP-TESTS` |
| 32 | Read the error message before guessing. | agent | |
| 33 | Suspect your application before the platform. | agent | |
| 34 | Prove assumptions in the real environment. | agent | |
| 35 | Learn a language that makes text manipulation cheap. | human | |
| 36 | Accept that software will fail and design for it. | agent | |
| 37 | State what each boundary promises and expects. | auto | `PP-CONTRACTS` |
| 38 | Fail fast instead of continuing with corrupted state. | auto | `PP-CONTRACTS` |
| 39 | Assert conditions that must never be false. | auto | `PP-CONTRACTS` |
| 40 | Release every resource you acquire. | auto | `PP-RESOURCES` |
| 41 | Keep mutable state and open resources in small, visible scopes. | auto | `PP-RESOURCES`, `PP-GLOBALS` |
| 42 | Change in small steps, check feedback, then continue. | auto | `PP-SMALL-STEPS` |
| 43 | Do not build for requirements you cannot yet see. | agent | speculative code |
| 44 | Reduce coupling so one change stays one change. | auto | `PP-ORTHO` |
| 45 | Tell objects to do work instead of pulling out their data. | agent | |
| 46 | Avoid reaching through long chains of objects. | auto | `PP-TRAINWRECK` |
| 47 | Avoid global mutable data. | auto | `PP-GLOBALS` |
| 48 | If state must be global, hide it behind an API. | agent | |
| 49 | Design around data transformations. | agent | |
| 50 | Pass state explicitly instead of hoarding it. | agent | |
| 51 | Prefer composition to deep inheritance. | auto | `PP-INHERIT` |
| 52 | Use interfaces to express polymorphism. | agent | |
| 53 | Contain services instead of inheriting from them. | agent | |
| 54 | Share behavior with mixins when the language supports them. | agent | |
| 55 | Move environment-specific values outside the application. | auto | `PP-CONFIG` |
| 56 | Model concurrency after the real workflow. | human | |
| 57 | Remove shared mutable state; it is the source of race conditions. | auto | `PP-SHARED-STATE`, `PP-TEST-HYGIENE` |
| 58 | Treat intermittent failures as concurrency suspects. | agent | |
| 59 | Use actors or message passing for concurrent state. | agent | |
| 60 | Let independent workers coordinate through a shared space. | agent | |
| 61 | Trust the discomfort that says the design is wrong. | agent | |
| 62 | Rely on understood behavior, not a lucky coincidence. | auto | `PP-COINCIDENCE` |
| 63 | Know the order of growth of your algorithms. | auto | `PP-COMPLEXITY` |
| 64 | Measure performance in the environment that matters. | agent | |
| 65 | Refactor while the code is still fresh. | auto | `PP-COMPLEXITY` |
| 66 | Use tests as feedback on design and coupling. | auto | `PP-TESTS`, `PP-TEST-HYGIENE` |
| 67 | Treat the test as the first user of your API. | auto | `PP-TESTS` |
| 68 | Build end-to-end in small slices. | auto | `PP-E2E` |
| 69 | Design for testability before writing the code. | agent | |
| 70 | Test ruthlessly before users find the bugs. | auto | `PP-TESTS` |
| 71 | Use property-based tests to challenge assumptions. | agent | |
| 72 | Keep the design simple and the attack surface small. | auto | `PP-COMPLEXITY` |
| 73 | Patch known security issues quickly. | agent | |
| 74 | Name for intent and rename when the intent changes. | auto | `PP-NAMING`, `PP-COMMENTS` |
| 75 | Accept that nobody knows the full requirements at the start. | human | |
| 76 | Co-create requirements with the people who will use the result. | human | |
| 77 | Learn requirements through a feedback loop. | human | |
| 78 | Observe users in their real context. | human | |
| 79 | Express policy as metadata instead of hardcoded logic. | auto | `PP-MAGIC` |
| 80 | Keep one shared glossary for the project. | agent | domain language |
| 81 | Find the real constraint before declaring a problem impossible. | human | |
| 82 | Review and pair instead of coding alone. | human | |
| 83 | Treat agility as a way of working, not a set of ceremonies. | human | |
| 84 | Keep teams small and stable. | human | |
| 85 | Schedule reflection, learning, and improvement. | human | |
| 86 | Organize teams around end-to-end capability. | human | |
| 87 | Adopt what works in your context, not what is fashionable. | human | |
| 88 | Deliver when users need it. | human | |
| 89 | Trigger builds, tests, and releases from version control. | auto | `PP-AUTOMATION` |
| 90 | Test early, often, and automatically. | auto | `PP-AUTOMATION` |
| 91 | A change is not done until the tests run. | auto | `PP-TESTS` |
| 92 | Inject faults to check that the tests can fail. | agent | |
| 93 | Test meaningful states, not just lines of code. | agent | |
| 94 | Turn every found bug into a regression test. | agent | |
| 95 | Automate repeated procedures. | auto | `PP-AUTOMATION` |
| 96 | Deliver business value, not just code. | human | |
| 97 | Sign your work and stand behind it. | human | |
| 98 | When failure happens, make sure nobody is harmed. | human | |
| 99 | Do not build tools whose main purpose is to enable harm. | human | |
| 100 | Make the work sustainable, share it, and keep it enjoyable. | human | |

## How to use this list

- For a small change, use the tips that apply to the decision in front of you.
- For a review, use the checklist in [`code-review.md`](code-review.md).
- For an audit, pair the scanner findings with the judgment questions in the report.
- Do not quote the book. Use these paraphrases and link to the official source.
