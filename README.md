# QTask

QTask is a small set of web apps for a computational chemist's working day: what to do today, a lab notebook, a literature radar, a 3D structure viewer and figure helpers, tied together by a control center. It runs in the browser on a Mac and on an iPhone, installs like an app, works offline once opened, and keeps the same data on every device through a private GitHub repository.

It is an adaptation of [CompChemKit](https://github.com/arvpinto/compchemkit) by Alexandre R. V. Pinto (MIT licence), trimmed to the parts I use. It adds a Tasks app, a reading list in the radar, sync between devices and iPhone-friendly backups.

**Open it:** https://ppaivaa.github.io/QTask/

## What is inside

| Suite | Apps |
|---|---|
| **Control center** | Today (needs attention, meetings, today's tasks, next 14 days, literature, in progress, last 7 days), Projects, Search, Apps, Backup and sync |
| **Lab notebook** | Research log, **Tasks**, **Meetings** (with points to present and action items), Deadlines, Idea board, Script planner |
| **Literature hub** | Radar (OpenAlex topics, with a **reading list**), Citations (your OpenAlex profile) |
| **Structure studio** | 3D viewer (3Dmol.js): PDB, mmCIF, GRO, XYZ, SDF, MOL2, PQR; PDB, AlphaFold and PubChem by ID |
| **Paper kit** | Plot guide (tested Python scripts for 31 chart types), Mechanism scheme editor (SVG and 600 dpi PNG) |

**Tasks** rank themselves. Each task has a priority (low, medium, high) and, optionally, a day to do it and a due date. Points are added up: priority 10 / 20 / 35, plus 45 if overdue, 35 if due today, 28 tomorrow, 20 in 2–3 days, 12 in 4–7 days and 6 in 8–14 days, plus 5 if planned for today. The total gives a level: 60 or more is *Do now*, 35 or more *Urgent*, 20 or more *Normal*, and below that *Can wait*. The Today view lists what is planned, what is overdue and the most urgent tasks you have not planned yet. Tasks left undone move to the next day on their own. End a quick entry with `!` to make it high priority.

**Meetings** are planned ahead and written up afterwards, in one place. Give a meeting a date, a time, a project and how often it repeats: every week, every 2 weeks, every month on the same day or on the same weekday (for example the third Tuesday), or every year. When a repeating meeting's day comes, the next one is planned on its own. Between meetings, add the points you want to present or discuss, from the meeting's card or from the control center's + button. Each meeting has a reminder (on the day, or 1 day to 2 weeks before). Inside that window, the control center's header names the meeting and the Today view lists its points. On the day and afterwards, the same meeting takes the notes, the decisions and the action items, with owners and due dates. Open actions from earlier meetings of the same series are shown again at the next one, so they can be ticked off there. Your own actions also appear on Today when they are due. Meetings you have not written up wait under *To write up* for two weeks. *Didn't happen* or *Skip this date* clears them.

## Install it as an app

QTask is one app: always add it from the control center page, so every suite opens inside the same window and shares the same data.

- **iPhone or iPad:** open the address in **Safari**, tap Share › **Add to Home Screen**.
- **Mac:** in **Safari** (macOS 14 or later), File › **Add to Dock**. In Chrome or Edge, use the install icon in the address bar.

## Sync between the Mac and the iPhone

Every device keeps its own copy in the browser. Sync keeps the copies in step through a **private** GitHub repository that only you can read. Each app's data is one file in `data/`, and every change is a commit, so the repository history is also a full backup.

Set it up once:

1. Create a **private, empty** repository for the data, for example `ppaivaa/QTask-data`.
2. Make a token for it on GitHub: Settings › Developer settings › Personal access tokens › **Fine-grained tokens** › Generate new token.
   - Repository access: **Only select repositories**, and pick the data repository.
   - Permissions › Repository permissions › **Contents: Read and write**.
   - Choose an expiry. When it expires, make a new token and connect again; nothing is lost.
3. In QTask, go to the control center › **Backup** › **Set up sync**. Paste the repository and the token, and give the device a name.
4. Repeat step 3 on every other device, with the same repository and token. If a device already has data, it asks whether to keep that data or use the copy in GitHub.

Changes sync a few seconds after you make them, when the app opens and every few minutes while it is open. If the same app was changed on two devices before they could sync, the newer edit wins. The other version is kept under *Versions replaced by a sync* in the Backup view, where you can restore it.

## Backups to a file (iCloud Drive)

Control center › Backup › **Download everything as one file**. On an iPhone, the share sheet opens: choose **Save to Files › iCloud Drive**. On a Mac, the file goes to Downloads. Restore it with **Restore… › From a file**, on any device. Each suite's Backup button can also save that suite on its own, and most apps have *Export backup* in their ⋮ menu.

## Alerts

A web app on the home screen cannot schedule its own notifications, so alerts go through your calendar instead. In **Deadlines** and in **Tasks**, the ⋮ menu has *Export calendar file*. Open the `.ics` file and the due dates go into Calendar with an alert. In **Meetings**, the 📅 button on a meeting (or ⋮ › *Export calendar file*) makes a repeating calendar event with an alert at the meeting's reminder and, when it has a start time, another 15 minutes before. The control center's Today view and its badge show everything that needs attention when you open QTask.

## Privacy

Your data stays in your browser and in your own private repository. Nothing else leaves the device except the lookups you ask for: Crossref for papers, OpenAlex for the radar and citations, and RCSB PDB, AlphaFold DB and PubChem for structures. The GitHub token and the OpenAlex key are stored only on each device. They are never synced and never written into backup files.

## Changing QTask

The pages are built from `src/` by `build.py`. It has no dependencies beyond Python 3.

```
src/static/                 shared files: suite-theme.js (colours), suite-sync.js (GitHub sync), service worker, icons
src/suites/_suite-shell.html    the frame of every suite page (bottom bar, Backup sheet, live reload)
src/suites/control-center/      the control center
src/suites/<suite>/apps/*.html  one complete page per app
build.py                    puts the apps into their suite pages and writes the site
tools/smoke.py              opens every page in headless Chromium and reports errors
tools/sync_test.py          two simulated devices syncing through a fake GitHub
tools/meetings_test.py      repeat rules, points to present, warnings and the calendar file
```

```bash
python3 build.py --serve          # build into dist/ and open http://127.0.0.1:8765/control-center.html
python3 build.py --out docs       # build the published copy (GitHub Pages serves docs/)
python3 build.py --name "New name" --out docs   # rename the app
```

The tests need Playwright: `pip install playwright && python3 -m playwright install chromium`.

**Publishing:** the site is the `docs/` folder of this repository. In the repository's Settings › Pages, choose *Deploy from a branch*, branch `main`, folder `/docs`. After a change, run `python3 build.py --out docs`, then commit and push.

## Licence

MIT, see [LICENSE](LICENSE). Based on CompChemKit © 2026 Alexandre R. V. Pinto. The structure viewer includes 3Dmol.js (BSD-3-Clause); see `docs/THIRD_PARTY_NOTICES.md`. If you publish figures made with the viewer, please cite Rego, N.; Koes, D. *Bioinformatics* **2015**, 31, 1322–1324.
