#!/usr/bin/env python3
"""Meetings: migration from the research log, repeat rules, points to present, the control center's
warnings and quick capture, and the calendar file. Runs against dist/ in headless Chromium.

    python3 build.py && python3 tools/meetings_test.py
"""
import datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smoke import serve  # noqa: E402
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []


def check(ok, what):
    print(("PASS " if ok else "FAIL ") + what)
    if not ok:
        FAILS.append(what)


def iso(d):
    return d.isoformat()


def nth_weekday(y, m, n, wd):  # wd: Monday=0 (Python), n=-1 for last
    if n < 0:
        last = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1))
        return last - dt.timedelta(days=(last.weekday() - wd) % 7)
    first = dt.date(y, m, 1)
    return first + dt.timedelta(days=(wd - first.weekday()) % 7 + 7 * (n - 1))


def add_month(y, m, k=1):
    m += k
    return y + (m - 1) // 12, (m - 1) % 12 + 1


def main():
    today = dt.date.today()
    seed = json.load(open(os.path.join(ROOT, "tools", "fixtures", "demo.json")))
    seed.pop("meetings.v1", None)
    # the demo's meeting stays in the log, the way older data looks
    seed["researchlog.v1"]["entries"].append({"id": "old-mt", "kind": "meeting", "title": "Supervision", "mtype": "supervision",
        "people": ["Prof"], "text": "Talked about chapter 2", "decisions": "", "proj": "Thesis", "date": iso(today - dt.timedelta(days=20)),
        "added": 1, "updated": 1, "actions": [{"id": "oa1", "text": "Send the chapter draft", "owner": "", "due": iso(today - dt.timedelta(days=2)), "done": False}]})
    # repeating series whose latest meeting is in the past: the next one must be made after today
    y, m = today.year, today.month
    py, pm = add_month(y, m, -1)
    first_thu_prev = nth_weekday(py, pm, 1, 3)
    last_thu_prev = nth_weekday(py, pm, -1, 3)
    series = [
        ("s-mn", {"f": "mn", "n": 1, "wd": 4}, iso(first_thu_prev)),
        ("s-ml", {"f": "ml", "wd": 4}, iso(last_thu_prev)),
        ("s-md", {"f": "md", "d": 31}, "2026-08-31"),
        ("s-w2", {"f": "w", "n": 2}, iso(today - dt.timedelta(days=13))),
        ("s-y", {"f": "y", "m": 1, "d": 29}, "2024-02-29"),
    ]
    items = [{"id": sid, "series": sid, "title": "Series " + sid, "mtype": "collab", "proj": "Consortium", "people": [], "date": d,
              "time": "14:00", "end": "", "where": "", "rep": rep, "warn": 3, "agenda": [], "text": "", "decisions": "", "actions": [],
              "pin": False, "added": 1, "updated": 1} for sid, rep, d in series]
    seed["meetings.v1"] = {"items": items}

    def after_today(f):
        d = f(None)
        while d <= today:
            d = f(d)
        return d

    def mn_next(d):
        base = d or first_thu_prev
        yy, mm = add_month(base.year, base.month)
        return nth_weekday(yy, mm, 1, 3)

    def ml_next(d):
        base = d or last_thu_prev
        yy, mm = add_month(base.year, base.month)
        return nth_weekday(yy, mm, -1, 3)

    def md_next(d):
        base = d or dt.date(2026, 8, 31)
        yy, mm = add_month(base.year, base.month)
        last = (dt.date(*add_month(yy, mm), 1) - dt.timedelta(days=1)).day
        return dt.date(yy, mm, min(31, last))

    def w2_next(d):
        return (d or today - dt.timedelta(days=13)) + dt.timedelta(days=14)

    def y_next(d):
        base = d or dt.date(2024, 2, 28)
        yy = base.year + 1
        return dt.date(yy, 2, 29) if yy % 4 == 0 and (yy % 100 or yy % 400 == 0) else dt.date(yy, 2, 28)

    expect = {"s-mn": after_today(mn_next), "s-ml": after_today(ml_next), "s-md": after_today(md_next),
              "s-w2": after_today(w2_next), "s-y": after_today(y_next)}

    with serve(8793) as base, sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True, accept_downloads=True)
        ctx.route("**/*", lambda r: r.abort() if not r.request.url.startswith(base) else r.continue_())
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("dialog", lambda d: d.accept())
        page.goto(base + "/suite-theme.js")
        page.evaluate("s=>{localStorage.clear();for(const [k,v] of Object.entries(s))localStorage.setItem(k,JSON.stringify(v))}", seed)
        ls = lambda k: json.loads(page.evaluate("k=>localStorage.getItem(k)", k) or "null")

        # ---------- the control center sees the next meetings before the app has made them ----------
        page.goto(base + "/control-center.html#today")
        page.wait_for_timeout(1200)
        today_html = page.inner_text("#v-today")
        check("Series s-w2" in today_html and "Meetings" in today_html, "Today lists the next meeting of a series the app has not made yet")
        check("Send the chapter draft" in today_html, "an overdue action from a meeting still in the log shows under Needs attention")
        sub = page.inner_text("#sub")
        check("Series s-w2 tomorrow 14:00" in sub, f"the header warns about a meeting inside its reminder window ({sub!r})")

        # ---------- opening the lab notebook moves the log's meetings over ----------
        page.goto(base + "/lab-notebook.html#log")
        page.wait_for_timeout(1500)
        lg, mt = ls("researchlog.v1"), ls("meetings.v1")
        check(not any(e.get("kind") == "meeting" for e in lg["entries"]), "no meetings left in the research log")
        ids = {x["id"] for x in mt["items"]}
        check({"x1007", "old-mt"} <= ids, "both log meetings are in Meetings, with their ids")
        old = next(x for x in mt["items"] if x["id"] == "old-mt")
        check(old["actions"][0]["text"] == "Send the chapter draft" and old["text"] == "Talked about chapter 2", "notes and actions came along")

        # ---------- the app makes the next meeting of each series ----------
        page.goto(base + "/lab-notebook.html#meetings")
        page.wait_for_timeout(1500)
        mt = ls("meetings.v1")
        for sid, want in expect.items():
            got = sorted(x["date"] for x in mt["items"] if x.get("series") == sid)
            check(got[-1] == iso(want) and len(got) == 2, f"{sid}: next meeting on {iso(want)} (got {got})")
        page.reload()
        page.wait_for_timeout(1200)
        check(len(ls("meetings.v1")["items"]) == len(mt["items"]), "opening the app again makes nothing twice")

        # ---------- a new monthly meeting, from the sheet ----------
        fr = page.frame_locator("iframe[title='Meetings']")
        fr.locator("#fab").click()
        y2, m2 = add_month(today.year, today.month)
        first_thu = nth_weekday(y2, m2, 1, 3)
        fr.locator("#mName").fill("Consortium meeting")
        fr.locator("#mType").select_option("collab")
        fr.locator("#mProj").fill("Consortium")
        fr.locator("#mDate").fill(iso(first_thu))
        fr.locator("#mDate").dispatch_event("change")
        fr.locator("#mTime").fill("14:00")
        fr.locator("#mEnd").fill("16:00")
        labels = fr.locator("#mRep option").all_inner_texts()
        check("Every month on the first Thursday" in labels, f"repeat choices follow the date ({labels})")
        fr.locator("#mRep").select_option(label="Every month on the first Thursday")
        fr.locator("#mWarn").select_option("7")
        fr.locator("#mWhere").fill("https://zoom.us/j/123")
        fr.locator("#mAddPt").click()
        fr.locator("#mAgenda .agrow input[type=text]").last.fill("MD of the variant: RMSD and key distances")
        fr.locator("#mform button[type=submit]").click()
        page.wait_for_timeout(400)
        mt = ls("meetings.v1")
        c = next(x for x in mt["items"] if x["title"] == "Consortium meeting")
        check(c["rep"] == {"f": "mn", "n": 1, "wd": 4} and c["series"] == c["id"], f"saved as a monthly series ({c['rep']})")
        check(c["warn"] == 7 and c["time"] == "14:00" and c["end"] == "16:00", "time and reminder saved")
        check([a["text"] for a in c["agenda"]] == ["MD of the variant: RMSD and key distances"], "the point to present is saved")

        # quick point from the card
        card = fr.locator(f".mt[data-id='{c['id']}']")
        card.locator(".addpt input").fill("Ask about the HPC allocation")
        card.locator(".addpt input").press("Enter")
        page.wait_for_timeout(300)
        c = next(x for x in ls("meetings.v1")["items"] if x["id"] == c["id"])
        check(len(c["agenda"]) == 2 and c["agenda"][1]["text"] == "Ask about the HPC allocation", "a point added from the card")

        # calendar file
        with page.expect_download() as dl:
            fr.locator(f".mt[data-id='{c['id']}'] [data-act='ics']").click()
        ics = open(dl.value.path(), encoding="utf-8").read()
        check("RRULE:FREQ=MONTHLY;BYDAY=1TH" in ics, "calendar file repeats on the first Thursday")
        check(f"DTSTART:{first_thu.strftime('%Y%m%d')}T140000" in ics and f"DTEND:{first_thu.strftime('%Y%m%d')}T160000" in ics, "local start and end times")
        check("TRIGGER:-P7D" in ics and "TRIGGER:-PT15M" in ics, "alerts a week before and 15 minutes before")
        check("Ask about the HPC allocation" in ics and "URL:https://zoom.us/j/123" in ics, "points and the link go into the event")

        # ---------- skip a date; delete the next one of a series stops it ----------
        nxt = next(x for x in ls("meetings.v1")["items"] if x.get("series") == "s-w2" and x["date"] > iso(today))
        fr.locator(f".mt[data-id='{nxt['id']}'] [data-act='edit']").click()
        fr.locator("#mSkip").click()
        page.wait_for_timeout(300)
        check(next(x for x in ls("meetings.v1")["items"] if x["id"] == nxt["id"]).get("skipped") is True, "Skip this date marks it skipped")
        nxt = next(x for x in ls("meetings.v1")["items"] if x.get("series") == "s-y" and x["date"] > iso(today))
        fr.locator(f".mt[data-id='{nxt['id']}'] [data-act='edit']").click()
        fr.locator("#mDel").click()
        page.wait_for_timeout(300)
        page.reload()
        page.wait_for_timeout(1200)
        left = [x for x in ls("meetings.v1")["items"] if x.get("series") == "s-y"]
        check(len(left) == 1 and left[0].get("rep") is None, "deleting the next meeting of a series stops it (no new one made)")

        # ---------- control center: Today, quick capture of points, projects ----------
        page.goto(base + "/control-center.html#today")
        page.wait_for_timeout(1200)
        check("Series s-w2" not in page.inner_text("#v-today").split("Last 7 days")[0], "a skipped meeting is not announced")
        # add points to the next s-mn meeting through + Point
        target = next(x for x in ls("meetings.v1")["items"] if x.get("series") == "s-mn" and x["date"] > iso(today))
        btn = page.locator(f"#s-meet [data-op='mt-point'][data-id='{target['id']}']")
        if btn.count():
            btn.click()
        else:
            page.locator("#fab").click(); page.locator(".seg [data-cap='meeting']").click(); page.locator("#mSel").select_option(target["id"])
        page.fill("#mPts", "- Slide on the new barrier\n- Timeline for the deliverable")
        page.locator("#capGo").click()
        page.wait_for_timeout(600)
        t2 = next(x for x in ls("meetings.v1")["items"] if x["id"] == target["id"])
        check([a["text"] for a in t2["agenda"]] == ["Slide on the new barrier", "Timeline for the deliverable"], "quick capture adds points to a coming meeting")
        # a new meeting from quick capture
        page.locator("#fab").click()
        page.locator(".seg [data-cap='meeting']").click()
        page.fill("#mTitle", "Group meeting")
        page.fill("#mDate", iso(today + dt.timedelta(days=5)))
        page.locator("#mDate").dispatch_event("change")
        page.locator("#mRep").select_option("w1")
        page.locator("#capGo").click()
        page.wait_for_timeout(600)
        g = next((x for x in ls("meetings.v1")["items"] if x["title"] == "Group meeting"), None)
        check(g is not None and g["rep"] == {"f": "w", "n": 1} and g["series"] == g["id"], "quick capture makes a weekly meeting")
        # tick an action from Today: it lives in Meetings now
        page.goto(base + "/control-center.html#today")
        page.wait_for_timeout(1000)
        meet = page.inner_text("#s-meet")
        check("Group meeting" in meet and "in 5 days" in meet and "weekly" in meet, f"Today's Meetings card shows the new weekly meeting")
        page.locator("#s-attn [data-op='act-done'][data-aid='oa1']").click()
        page.wait_for_timeout(600)
        oa = next(x for x in ls("meetings.v1")["items"] if x["id"] == "old-mt")["actions"][0]
        check(oa["done"] is True, "ticking a meeting action on Today saves it in Meetings")
        page.goto(base + "/control-center.html#projects")
        page.wait_for_timeout(800)
        page.locator("[data-op='proj']", has_text="Consortium").first.click()
        page.wait_for_timeout(400)
        check("Consortium meeting" in page.inner_text("#v-projects"), "the Consortium project page lists its meetings")
        page.goto(base + "/control-center.html#search")
        page.fill("#q", "HPC allocation")
        page.wait_for_timeout(500)
        check("Consortium meeting" in page.inner_text("#qOut"), "search finds a meeting by one of its points")

        check(not errs, f"no page errors ({errs[:3]})")
        b.close()
    print(f"\n{'All passed' if not FAILS else str(len(FAILS)) + ' failed'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
