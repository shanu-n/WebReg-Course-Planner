#!/usr/bin/env python3
"""Content pages for the ad-supported build variant.

build_site.py imports this when WEBREG_ADS=1 and calls build_pages() to emit
the About / Guide / FAQ / Privacy / Terms pages into site/. These give the
site real, navigable, original content (what AdSense wants to see) around the
planner tool. The tool page itself is left visually unchanged — only gutter
ad rails + a small footer nav are added (see build_site.regen_index).

All pages share the WebReg chrome (banner + disclaimer + section nav) and the
same stylesheet, so the site feels like one product.
"""

# ---- shared page shell ----------------------------------------------------

NAV = [
    ("./", "Planner", "planner"),
    ("guide.html", "Planning Guide", "guide"),
    ("faq.html", "FAQ", "faq"),
    ("about.html", "About", "about"),
    ("privacy.html", "Privacy", "privacy"),
]

# Where the real Google AdSense <ins> goes once the account is approved.
# Until then these render as neutral placeholder boxes.
AD_RAILS = """
<div class="ad-rail ad-left"><div class="ad-slot"><span class="ad-tag">Advertisement</span><span>160&times;600</span></div></div>
<div class="ad-rail ad-right"><div class="ad-slot"><span class="ad-tag">Advertisement</span><span>160&times;600</span></div></div>
<!-- AdSense: replace each .ad-slot inner with
     <ins class="adsbygoogle" style="display:inline-block;width:160px;height:600px"
          data-ad-client="ca-pub-XXXX" data-ad-slot="YYYY"></ins>
     and add the loader <script> (see privacy.html) in <head>. -->
"""


def _nav(active):
    links = ""
    for href, label, key in NAV:
        cls = ' class="active"' if key == active else ''
        links += f'<a href="{href}"{cls}>{label}</a>'
    return f'<nav class="site-nav">{links}</nav>'


def shell(title, description, active, body, css_v):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{description}">
<meta name="robots" content="index,follow">
<link rel="stylesheet" href="css/webreg.css?v={css_v}">
<script data-goatcounter="https://ssssss.goatcounter.com/count"
        async src="//gc.zgo.at/count.js"></script>
</head>
<body>
<div class="tl-banner">
  <span class="tl-brand">Functional Course Planner not TSS Slop</span>
  <span class="tl-wordmark"><span class="tl-unofficial">Unofficial</span>UC San Diego</span>
</div>
<div class="disclaimer-strip">
  Unofficial, student-made planning tool &mdash; <b>not affiliated with, endorsed by, or operated by UC San Diego.</b>
  &ldquo;UC San Diego,&rdquo; &ldquo;Triton,&rdquo; and &ldquo;WebReg&rdquo; are marks of the university, used here only to describe what this tool helps with.
</div>
{_nav(active)}
<div class="content">
{body}
</div>
<div class="copyright-note" style="text-align:center;padding:16px 0 28px;">&copy; 2026 Sahir Sharma &middot;
  <a href="about.html">About</a> &middot; <a href="privacy.html">Privacy</a> &middot;
  <a href="terms.html">Terms</a> &middot;
  <a href="https://github.com/SahirSSharma/WebReg-Course-Planner" target="_blank" rel="noopener">GitHub</a> &middot;
  <a href="mailto:sas063@ucsd.edu">Feedback</a></div>
{AD_RAILS}
</body>
</html>
"""


# ---- page bodies ----------------------------------------------------------

GUIDE = """
<h1>How to Plan Your UCSD Schedule (the Right Way)</h1>
<p class="lede">Enrollment appointments come fast, and the good sections fill in minutes. A schedule you've already built and stress-tested is the difference between the classes you want and the leftovers. Here's how to plan a clean, conflict-free quarter.</p>

<p><a class="cta" href="./">Open the planner &rarr;</a></p>

<h2>1. Plan before your enrollment appointment</h2>
<p>Every student gets an assigned enrollment appointment (your "first pass"), and popular courses fill within minutes of it opening. If you walk in without a plan, you'll waste your window searching. Build your ideal schedule ahead of time, save a backup or two, and on enrollment day you're just clicking through a list you already trust.</p>
<div class="callout">This tool is for <b>planning only</b> &mdash; you still enroll in UCSD's official system. Think of it as your whiteboard before the real thing.</div>

<h2>2. Understand the section types</h2>
<p>A single UCSD course is usually made of several linked meetings. When you plan a course you're really picking a compatible set of them:</p>
<table>
<tr><th>Code</th><th>Meeting</th><th>What it is</th></tr>
<tr><td>LE</td><td>Lecture</td><td>The main class, taught by the professor. Usually the same for everyone in the course.</td></tr>
<tr><td>DI</td><td>Discussion</td><td>Smaller section led by a TA. You pick one that fits your week.</td></tr>
<tr><td>LA</td><td>Lab</td><td>Hands-on section (sciences, engineering). Often the longest single block.</td></tr>
<tr><td>SE</td><td>Seminar</td><td>Small discussion-style course, common in upper-division and grad classes.</td></tr>
<tr><td>FI</td><td>Final</td><td>The final exam &mdash; a fixed date and time, not a weekly meeting.</td></tr>
</table>
<p>The planner groups these for you, so when you add a course you get the lecture plus a discussion/lab that don't collide.</p>

<h2>3. Read a course the way the pros do</h2>
<p>For each section the planner shows the days, time, building and room, instructor, and seat counts. A few things worth checking every time:</p>
<ul>
<li><b>Seats vs. limit.</b> A section that's already near full before your appointment is a coin flip &mdash; line up a backup.</li>
<li><b>Instructor.</b> The same course can feel completely different depending on who teaches it. Cross-check names on <a href="https://cape.ucsd.edu/" target="_blank" rel="noopener">CAPE</a> (UCSD's official Course And Professor Evaluations) and <a href="https://www.ratemyprofessors.com/" target="_blank" rel="noopener">Rate My Professors</a>.</li>
<li><b>Location.</b> Two classes 10 minutes apart on opposite ends of campus is a real problem &mdash; more on that below.</li>
</ul>

<h2>4. Build a conflict-free week in Calendar view</h2>
<p>Add every course you're considering, then switch to <b>Calendar</b>. Overlaps are obvious at a glance, and the planner flags time conflicts for you. Aim for:</p>
<ul>
<li>No overlapping meetings (the tool warns you, but a visual check is faster).</li>
<li>Breaks long enough to eat and walk &mdash; back-to-back classes across campus are exhausting by week three.</li>
<li>A shape that fits how you actually work: if you're useless at 8am, don't schedule an 8am lecture you'll skip.</li>
</ul>

<h2>5. Check your finals early &mdash; before you enroll</h2>
<p>It's easy to build a perfect weekly schedule and discover too late that two of your finals are stacked on the same afternoon. Use the <b>Finals</b> view to see all your exam dates and times up front, and rebalance while you still can.</p>

<h2>6. Have a waitlist strategy</h2>
<p>If a section is full you can often waitlist it. Waitlists move &mdash; students drop, add, and swap constantly in the first weeks &mdash; but never rely on one:</p>
<ul>
<li>Plan a realistic backup for any full or nearly-full course.</li>
<li>Prefer sections with open seats for your first pass; save waitlist gambles for second pass.</li>
<li>Keep attending the class you're waitlisted for &mdash; many professors add from the list in order.</li>
</ul>

<h2>7. Balance units and workload</h2>
<p>Full-time is typically 12+ units, and most students take 12&ndash;16. But raw units hide the real load: three writing-heavy courses is harder than four with problem sets. Mix formats, and be honest about which quarters (recruiting, a heavy lab, an internship) should be lighter.</p>

<h2>8. Know your college and GE requirements</h2>
<p>UCSD's colleges each have their own general-education requirements, so two students in the same major can have very different to-do lists. Confirm what you actually need from official sources before locking a schedule:</p>
<ul>
<li>Your <a href="https://students.ucsd.edu/academics/advising/colleges-advising.html" target="_blank" rel="noopener">college's academic advising</a> page for GE requirements.</li>
<li>The <a href="https://catalog.ucsd.edu/" target="_blank" rel="noopener">UCSD General Catalog</a> for major requirements and course descriptions.</li>
<li>Your <a href="https://act.ucsd.edu/studentDegreeAudit/" target="_blank" rel="noopener">Degree Audit</a> to see what's left.</li>
</ul>

<h2>9. Mind the walk between classes</h2>
<p>UCSD is big. A discussion in one corner and a lecture in another with a 10-minute passing period can mean speed-walking every week. The planner's <b>Map</b> view plots your classes and estimates the walk between them (and from your dorm), so you can catch an impossible transition before you commit to it.</p>

<h2>10. Enrollment-day checklist</h2>
<ol>
<li>Know your appointment time (check the official <a href="https://students.ucsd.edu/academics/enrollment/calendars/index.html" target="_blank" rel="noopener">enrollment calendar</a>).</li>
<li>Have your planned schedule open, plus a backup schedule.</li>
<li>Confirm prerequisites and any needed authorization ahead of time.</li>
<li>Enroll the hardest-to-get course first.</li>
<li>Verify everything in the official system once you're done.</li>
</ol>

<div class="callout warn">Course data here is a snapshot and can lag the official system. Always confirm sections, seats, times, and requirements in UCSD's official tools before you enroll.</div>

<p><a class="cta" href="./">Start planning &rarr;</a></p>
"""

FAQ = """
<h1>Frequently Asked Questions</h1>
<p class="lede">Quick answers about what this planner is, what it isn't, and how to use it safely.</p>

<h3>Is this the official UCSD registration site?</h3>
<p>No. This is an independent, student-made planning tool. It is <b>not affiliated with, endorsed by, or operated by UC San Diego</b>. You cannot enroll here &mdash; use it to plan, then register in UCSD's official system.</p>

<h3>Can I actually enroll in classes with this?</h3>
<p>No &mdash; it's a planner. It helps you build and compare schedules, spot conflicts, and check finals and walking distances. Enrollment happens only through UCSD's official registration system.</p>

<h3>How current is the course data?</h3>
<p>The catalog is a periodic snapshot pulled from UCSD's official course data. The "Course data as of" date is shown in the footer. Seat counts in particular change constantly during enrollment, so treat them as a recent estimate and confirm in the official system.</p>

<h3>Which term does it cover?</h3>
<p>Fall 2026 (FA26), with every department's courses, sections, professors, times, rooms, and seats.</p>

<h3>Is my data private? Do I need an account?</h3>
<p>No account, no login. Your schedule is saved only in your own browser (local storage) &mdash; it never leaves your device to us. See the <a href="privacy.html">Privacy Policy</a> for details on analytics and ads.</p>

<h3>Does it work on my phone?</h3>
<p>Yes. The planner is fully responsive and works on phones and tablets, not just laptops.</p>

<h3>Is it free?</h3>
<p>Completely free. It's supported by unobtrusive ads on wide screens and optional tips &mdash; never a paywall.</p>

<h3>Why does it look like the old WebReg?</h3>
<p>Because the old WebReg was fast and clear, and a lot of students prefer it to the newer interface. This is a from-scratch tool built to feel familiar &mdash; it just plans; it doesn't touch registration.</p>

<h3>I found a bug or something's wrong. How do I report it?</h3>
<p>Email <a href="mailto:sas063@ucsd.edu">sas063@ucsd.edu</a>. Bug reports and course-data corrections are genuinely appreciated.</p>

<p><a class="cta" href="./">Back to the planner &rarr;</a></p>
"""

ABOUT = """
<h1>About This Planner</h1>
<p class="lede">A fast, familiar way to plan your UC San Diego schedule &mdash; built by a student, for students.</p>

<h2>Why it exists</h2>
<p>Planning a quarter should take minutes, not fight you. This tool brings back the quick, no-nonsense feel of the classic scheduling experience: search a department, see real sections with professors, times, rooms, and seats, and drop them onto a schedule you can actually read. No loading spinners, no dead ends.</p>

<h2>What it does</h2>
<ul>
<li>Search every Fall 2026 course and section with real instructors, times, rooms, and seat counts.</li>
<li>Plan multiple schedules and compare them side by side.</li>
<li>See your week in a calendar, catch time conflicts automatically, and check your finals up front.</li>
<li>Add your own weekly events (work, clubs, gym) so your plan reflects your real life.</li>
<li>See the walking distance between classes &mdash; and from your dorm &mdash; on a campus map.</li>
</ul>

<h2>Where the data comes from</h2>
<p>Course information is drawn from UCSD's official course data and refreshed periodically; the "as of" date is shown in the footer. Because it's a snapshot, always confirm details in the official system before enrolling.</p>

<h2>Not affiliated with UC San Diego</h2>
<p>This is an independent project. It is <b>not affiliated with, endorsed by, or operated by UC San Diego</b>. "UC San Diego," "Triton," and "WebReg" are marks of the university, referenced here only to describe what the tool helps with. It does not connect to registration and stores nothing about you on a server.</p>

<h2>Who made it &amp; how to reach me</h2>
<p>Built and maintained by Sahir Sharma, a UCSD student. Feedback, bug reports, and data corrections: <a href="mailto:sas063@ucsd.edu">sas063@ucsd.edu</a>. The source is on <a href="https://github.com/SahirSSharma/WebReg-Course-Planner" target="_blank" rel="noopener">GitHub</a>.</p>

<p><a class="cta" href="./">Open the planner &rarr;</a></p>
"""

PRIVACY = """
<h1>Privacy Policy</h1>
<p class="lede">Last updated: July 2026. Plain-English summary: no account, we don't collect personal information, and your schedule stays in your own browser.</p>

<h2>Information we collect</h2>
<p>We do not ask for or store any personal information, and there is no login. Specifically:</p>
<ul>
<li><b>Your schedule</b> is saved only in your browser's local storage, on your device. It is never transmitted to or stored by us.</li>
<li><b>Anonymous usage analytics.</b> We use <a href="https://www.goatcounter.com/" target="_blank" rel="noopener">GoatCounter</a>, a privacy-friendly analytics tool, to count page views. It does not use tracking cookies and does not collect personal data.</li>
</ul>

<h2>Advertising and cookies</h2>
<p>This site is supported by advertising. We may use Google AdSense to display ads. Third-party vendors, including Google, use cookies to serve ads based on your prior visits to this and other websites.</p>
<ul>
<li>Google's use of advertising cookies enables it and its partners to serve ads to you based on your visits to this and other sites.</li>
<li>You can opt out of personalized advertising by visiting <a href="https://www.google.com/settings/ads" target="_blank" rel="noopener">Google Ads Settings</a>.</li>
<li>You can learn about third-party ad vendors and opt out via <a href="https://www.aboutads.info/choices/" target="_blank" rel="noopener">aboutads.info/choices</a> and <a href="https://www.youronlinechoices.eu/" target="_blank" rel="noopener">youronlinechoices.eu</a>.</li>
<li>Review <a href="https://policies.google.com/technologies/partner-sites" target="_blank" rel="noopener">how Google uses information from sites that use its services</a>.</li>
</ul>

<h2>Third-party services</h2>
<p>We rely on GitHub Pages (hosting), GoatCounter (analytics), Google AdSense (advertising), and OpenStreetMap (map tiles for the campus map). Each operates under its own privacy policy.</p>

<h2>Children's privacy</h2>
<p>This site is intended for university students and the general public and is not directed at children under 13. We do not knowingly collect personal information from children.</p>

<h2>Your choices</h2>
<p>You can clear your saved schedule at any time by clearing your browser's local storage for this site. You can disable cookies in your browser and opt out of personalized ads using the links above.</p>

<h2>Changes</h2>
<p>We may update this policy; material changes will be reflected by the "last updated" date above.</p>

<h2>Contact</h2>
<p>Questions about this policy: <a href="mailto:sas063@ucsd.edu">sas063@ucsd.edu</a>.</p>
"""

TERMS = """
<h1>Terms of Use</h1>
<p class="lede">Last updated: July 2026. By using this site you agree to the following.</p>

<h2>Planning tool, not registration</h2>
<p>This site is a free, unofficial schedule-planning tool. It does not enroll you in classes and does not connect to any registration system. All enrollment must be done through UC San Diego's official systems.</p>

<h2>No affiliation with UC San Diego</h2>
<p>This site is an independent project and is <b>not affiliated with, endorsed by, sponsored by, or operated by UC San Diego</b>. "UC San Diego," "UCSD," "Triton," and "WebReg" are marks of their respective owners and are used here only nominatively, to describe what this tool helps you do.</p>

<h2>Accuracy and "as is"</h2>
<p>Course data is a periodic snapshot and may be incomplete, outdated, or incorrect &mdash; seat counts especially change constantly. The site is provided "as is," without warranties of any kind. <b>Always verify sections, times, seats, prerequisites, and requirements in UC San Diego's official systems before making enrollment decisions.</b> You are responsible for your own registration.</p>

<h2>Limitation of liability</h2>
<p>To the fullest extent permitted by law, the creator is not liable for any loss or damage arising from your use of, or reliance on, this site or its data.</p>

<h2>Acceptable use</h2>
<p>Don't use the site to break the law, disrupt the service, or scrape it abusively. The underlying source code is released under the MIT License; see the project's <a href="https://github.com/SahirSSharma/WebReg-Course-Planner" target="_blank" rel="noopener">GitHub</a>.</p>

<h2>Contact</h2>
<p>Questions: <a href="mailto:sas063@ucsd.edu">sas063@ucsd.edu</a>.</p>
"""

PAGES = [
    ("guide.html", "How to Plan Your UCSD Schedule — Unofficial UCSD Course Planner",
     "A practical guide to planning a conflict-free UC San Diego schedule: section types, finals, waitlists, workload, GE requirements, and enrollment-day tips.",
     "guide", GUIDE),
    ("faq.html", "FAQ — Unofficial UCSD Course Planner",
     "Answers about the unofficial UCSD course planner: what it is, data freshness, privacy, mobile support, and how to report bugs.",
     "faq", FAQ),
    ("about.html", "About — Unofficial UCSD Course Planner",
     "About the unofficial, student-made UC San Diego course planner: why it exists, what it does, where the data comes from, and who made it.",
     "about", ABOUT),
    ("privacy.html", "Privacy Policy — Unofficial UCSD Course Planner",
     "Privacy policy: no account, schedule saved only in your browser, anonymous analytics, and how advertising cookies work.",
     "privacy", PRIVACY),
    ("terms.html", "Terms of Use — Unofficial UCSD Course Planner",
     "Terms of use for the unofficial UCSD course planner, including the no-affiliation notice and the accuracy disclaimer.",
     "terms", TERMS),
]


def build_pages(out_dir, css_v):
    """Write every content page into out_dir. Returns the filenames written."""
    written = []
    for fname, title, desc, active, body in PAGES:
        (out_dir / fname).write_text(shell(title, desc, active, body, css_v))
        written.append(fname)
    return written
