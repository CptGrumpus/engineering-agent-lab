# LinkedIn update: handoff

Written 2026-11-24, 08:00 EST, on the desktop. This is for the Claude session on the laptop, which has one job: help Justin update his LinkedIn profile. **Justin deletes this file when the profile is done.** Modelling continues on the desktop and phone, so this session doesn't touch studies, `site/` or `docs/`.

This repo is public. Don't write personal details (employers, dates, email, salary, applications) into this file or any other committed file. Keep them in the chat.

## Goal

Update the profile so a contract client or hiring manager who clicks through from the portfolio, or finds Justin on LinkedIn first, sees a credible, experienced mechanical engineer who does verified simulation work and can take remote contract work. The target is contract modelling and AI-training work in mechanical engineering: turning requirements into a model, solving it, and judging the result against physical and design limits.

Then the portfolio gets a LinkedIn link next to the email button. That's [DASHBOARD.md](DASHBOARD.md) item H2, now "Waiting on me".

## What to produce, for Justin to paste in himself

You can't edit LinkedIn. Draft the text in chat, and Justin pastes it. Suggested order:

1. **Headline** (220 characters max). Mechanical engineer, simulation and verification, open to remote contract work. Offer two or three options.
2. **About** (2,600 characters max; the first roughly 300 show before "see more", so put the offer there). In plain words: what he does, how (requirement → model → independent check → verdict with stated uncertainty), the breadth (see the capability table in [PORTFOLIO.md](PORTFOLIO.md)), and the call to action with the portfolio link.
3. **Featured**: links with a one-line description each.
   - Portfolio home: https://cptgrumpus.github.io/engineering-agent-lab/
   - Evaluation tasks with graders (the AI-training angle): https://cptgrumpus.github.io/engineering-agent-lab/grading.html
   - Pressure vessel nozzle, design by analysis: https://cptgrumpus.github.io/engineering-agent-lab/pressure-vessel-nozzle.html
   - Bracket optimisation (the featured study on the home page): https://cptgrumpus.github.io/engineering-agent-lab/bracket-optimisation.html
   - Sample client deliverable (coolant-channel memo): https://cptgrumpus.github.io/engineering-agent-lab/coolant-channel.html
   - Ask Justin whether he'd rather feature the bolted joint, the roller contact or the traction motor instead of one of these.
4. **Experience**: a "Projects" or self-employed entry for the portfolio work: independent simulation portfolio, 2026, with 3 to 5 bullets of results that each link to their evidence. His past roles are his to supply. Help tighten the wording, but don't invent anything.
5. **Skills** (LinkedIn lets him pin a few): finite element analysis, CFD, heat transfer, contact and bolted joints, fatigue and fracture, vibration, pressure vessel design by analysis, verification and validation, Python, CalculiX, OpenFOAM, Gmsh, CadQuery, FreeCAD. Add the commercial tools he has actually used (see below).
6. **Open to work**: settings for contract and remote, visible to recruiters only or to everyone. That's his choice.

## Ask Justin before drafting

The repo doesn't hold his background, so ask for:

- His years of experience, the kinds of roles he's held, and the industries (the repo only says automotive). Ask how specific he wants to be about employer names.
- His education.
- Which commercial tools he has used, and at what level (ANSYS, Abaqus, Nastran, STAR-CCM+, Fluent, CAD packages). This also settles DASHBOARD H3, a line on the site saying which commercial tools the methods carry over to.
- His current headline and About text, if he wants to keep anything from them.
- Whether to draft the one-page CV at the same time (DASHBOARD H1). Most of the content overlaps.

## Rules carried over from the desktop

- Use only facts Justin gives you or that the repo shows. Every claim about the portfolio should match a page on the site; don't round up counts or results.
- Plain, direct writing: short sentences, no buzzwords, no sales tone. He decided against a services list, so describe the work, not offers.
- His name is shown publicly on the site. That's settled, so don't ask about it.
- Never put his contact email in a committed file. The site stores it encoded.

## When the profile is done

1. Get the public profile URL (linkedin.com/in/...).
2. On the laptop: `git pull`, then set DASHBOARD.md H2's "Needs from me" to the URL and its status to "Ready to add to the site". Delete this file, and commit and push both in one commit. The desktop session adds the link to the site, since the site build runs there.
3. If H1 (CV) or H3 (commercial tools) got answers, add them to those rows as well, without personal details beyond what Justin approves for the public repo.
