"""
DHM CV Optimisation Report — HTML Generator
--------------------------------------------
Produces a fully self-contained HTML string (all CSS inline, images base64-
embedded) ready for WeasyPrint → PDF conversion.
"""

import base64
import os
import re
from datetime import datetime

# ── Asset directory ────────────────────────────────────────────────────────────
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def _embed(filename):
    """Return a data-URI string for an image file, or empty string if missing."""
    path = os.path.join(ASSETS_DIR, filename)
    if not os.path.exists(path):
        return ''
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    mime = {'png': 'image/png', 'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg', 'svg': 'image/svg+xml'}.get(ext, 'image/png')
    with open(path, 'rb') as fh:
        return f'data:{mime};base64,{base64.b64encode(fh.read()).decode()}'


def _parse_priority(title):
    """
    Extract [HIGH PRIORITY] / [MEDIUM PRIORITY] tag from a title string.
    Returns (clean_title, 'high'|'medium').
    """
    title = str(title)
    priority = 'high' if re.search(r'\bHIGH\b', title, re.I) else 'medium'
    clean = re.sub(r'\s*[\[\(](HIGH|MEDIUM|LOW)\s*PRIORITY[\]\)]', '', title, flags=re.I).strip()
    return clean, priority


def _esc(text):
    """Minimal HTML escaping for user-supplied strings."""
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))


# ══════════════════════════════════════════════════════════════════════════════
def build_report_html(cv_data):
    """
    Generate the complete HTML string for one client's CV Optimisation Report.

    Expected cv_data keys:
      name        str   – client full name
      tagline     str   – e.g. "Head of Marketing — targeting VP / Director roles"
      changelog   list  – [{'title': str, 'text': str}, …]
      gap_report  list  – [{'title': str (may contain [HIGH/MEDIUM PRIORITY]),
                             'text': str}, …]
    """
    name       = _esc(cv_data.get('name', 'Client'))
    tagline    = _esc(cv_data.get('tagline', ''))
    changelog  = cv_data.get('changelog', [])
    gap_report = cv_data.get('gap_report', [])
    date_str   = datetime.now().strftime('%B %Y')

    # ── Assets ────────────────────────────────────────────────────────────────
    logo_src = _embed('DHM_App_Logo.png')
    sig_src  = _embed('DHM_Report_Signature_V3.png')

    if logo_src:
        logo_html = f'<img class="cover__logo" src="{logo_src}" alt="Dear Hiring Manager">'
    else:
        logo_html = (
            '<div style="font-family:Georgia,serif;font-size:20pt;font-weight:400;'
            'letter-spacing:-0.01em;line-height:1.1;">'
            'Dear Hiring Manager<span style="color:#DC6A63;">,</span>'
            '<div style="font-family:Arial,sans-serif;font-size:7.5pt;font-weight:700;'
            'letter-spacing:0.22em;text-transform:uppercase;color:#DC6A63;margin-top:3pt;">'
            'Career Coaching</div></div>'
        )

    sig_html = (
        f'<img src="{sig_src}" alt="Brendan Johns" '
        f'style="width:110mm;max-width:100%;height:auto;display:block;">'
    ) if sig_src else ''

    # ── Page 4: changelog items ───────────────────────────────────────────────
    change_items_html = ''
    for i, item in enumerate(changelog, 1):
        t = _esc(item.get('title', ''))
        p = _esc(item.get('text', ''))
        change_items_html += f'''
      <article class="change">
        <div class="change__num">{i:02d}</div>
        <div class="change__body">
          <h3>{t}</h3>
          <p>{p}</p>
        </div>
      </article>'''

    # ── Page 5: gap report / assessment items ─────────────────────────────────
    assess_items_html = ''
    for i, item in enumerate(gap_report, 1):
        raw_title = item.get('title', '')
        body_text = _esc(item.get('text', ''))
        title, priority = _parse_priority(raw_title)
        title = _esc(title)
        label      = 'High priority' if priority == 'high' else 'Medium priority'
        rail_bg    = '#DC6A63' if priority == 'high' else '#000000'
        tag_style  = ('background:#DC6A63;color:#fff;border-color:#DC6A63;'
                      if priority == 'high' else '')
        assess_items_html += f'''
      <article class="assess">
        <div class="assess__rail" style="background:{rail_bg};"></div>
        <div class="assess__body">
          <div class="assess__head">
            <div class="assess__index">Item {i:02d}</div>
            <div class="assess__tag" style="{tag_style}">{label}</div>
          </div>
          <h3 class="assess__title">{title}</h3>
          <p>{body_text}</p>
        </div>
      </article>'''

    # ══════════════════════════════════════════════════════════════════════════
    # Full HTML document
    # ══════════════════════════════════════════════════════════════════════════
    return f'''<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8"/>
<title>CV Optimisation Report — {name}</title>
<style>
/* ── Fonts ── */

/* ── Reset ── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ margin: 0; padding: 0; background: #E9E7E2; }}
body {{
  font-family: Liberation Sans, Arial, Helvetica, sans-serif;
  color: #000;
  font-size: 10.5pt;
  line-height: 1.55;
}}

/* ── Doc wrapper ── */
.doc {{
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12mm;
  padding: 20mm 0 40mm;
}}

/* ── A4 page ── */
.page {{
  position: relative;
  width: 210mm;
  min-height: 297mm;
  background: #fff;
  padding: 22mm;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}

/* ── Page header ── */
.page__header {{
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-bottom: 6mm;
  border-bottom: 1px solid #000;
  margin-bottom: 10mm;
  font-size: 8.5pt;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 600;
}}
.page__header .lhs {{ color: #000; }}
.page__header .rhs {{ color: #DC6A63; }}

/* ── Page footer ── */
.page__footer {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 6mm;
  border-top: 1px solid #000;
  margin-top: auto;
  font-size: 8pt;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #000;
  font-weight: 500;
}}
.page__footer .page-no {{ color: #DC6A63; font-weight: 700; }}
.comma-wink {{ color: #DC6A63; font-family: Georgia, serif; font-style: italic; font-weight: 400; }}

/* ══ COVER ══ */
.cover {{ display: flex; flex-direction: column; }}
.cover__top {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding-bottom: 6mm;
  border-bottom: 1px solid #000;
}}
.cover__logo {{ height: 26mm; width: auto; }}
.cover__meta {{
  text-align: right;
  font-size: 8.5pt;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #000;
  line-height: 1.7;
  font-weight: 600;
}}
.cover__meta .coral {{ color: #DC6A63; }}
.cover__body {{
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 10mm 0;
}}
.cover__eyebrow {{
  font-size: 9pt;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #DC6A63;
  margin-bottom: 10mm;
  display: flex;
  align-items: center;
  gap: 12px;
}}
.cover__eyebrow::before {{
  content: "";
  width: 28px;
  height: 1px;
  background: #DC6A63;
  display: inline-block;
}}
.cover__title {{
  font-size: 56pt;
  font-weight: 700;
  line-height: 0.95;
  letter-spacing: -0.035em;
  margin: 0;
}}
.cover__title .coral {{ color: #DC6A63; font-style: normal; }}
.cover__subtitle {{
  margin-top: 10mm;
  font-size: 13pt;
  font-weight: 400;
  line-height: 1.35;
  max-width: 140mm;
  color: #000;
  letter-spacing: -0.005em;
}}
.cover__subtitle strong {{ font-weight: 600; }}
.cover__client {{
  margin-top: 12mm;
  display: flex;
  align-items: stretch;
  border-top: 1px solid #000;
  border-bottom: 1px solid #000;
  padding: 5mm 0;
}}
.cover__client > div {{
  flex: 1;
  padding-right: 8mm;
}}
.cover__client > div + div {{
  border-left: 1px solid #000;
  padding-left: 8mm;
  padding-right: 0;
}}
.cover__client .label {{
  font-size: 8pt;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #DC6A63;
  display: block;
  margin-bottom: 3mm;
}}
.cover__client .value {{
  font-size: 12pt;
  font-weight: 600;
  letter-spacing: -0.01em;
}}
.cover__client .value small {{
  display: block;
  font-size: 9pt;
  font-weight: 400;
  color: #000;
  letter-spacing: 0;
  margin-top: 2mm;
  line-height: 1.4;
}}
.cover__bottom {{
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-top: 6mm;
  border-top: 1px solid #000;
  font-size: 8.5pt;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-weight: 600;
}}
.cover__bottom .tag {{ color: #DC6A63; }}

/* ══ WELCOME ══ */
.welcome__hero {{ margin-bottom: 10mm; }}
.kicker {{
  font-size: 9pt;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #DC6A63;
  font-weight: 700;
  margin-bottom: 5mm;
}}
.welcome__hero h1 {{
  font-size: 34pt;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.02;
  margin: 0;
}}
.welcome__hero h1 .coral {{ color: #DC6A63; }}
.welcome__body {{
  display: flex;
  gap: 10mm;
  padding-top: 8mm;
  border-top: 1px solid #000;
}}
.meta-col {{
  width: 55mm;
  flex-shrink: 0;
  font-size: 8.5pt;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 600;
  line-height: 1.8;
}}
.meta-col .label {{ color: #DC6A63; display: block; }}
.meta-col .group + .group {{ margin-top: 5mm; }}
.meta-col .value {{
  text-transform: none;
  letter-spacing: 0;
  font-weight: 500;
  font-size: 10pt;
  display: block;
  margin-top: 1mm;
}}
.welcome__prose {{ flex: 1; }}
.welcome__prose p {{ font-size: 11pt; line-height: 1.6; margin: 0 0 4mm; }}
.welcome__prose .big {{
  font-size: 13pt;
  font-weight: 500;
  letter-spacing: -0.005em;
  margin-bottom: 4mm;
}}
.welcome__toc {{
  margin-top: 7mm;
  padding-top: 5mm;
  border-top: 1px solid #000;
}}
.welcome__toc-label {{
  font-size: 9pt;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #DC6A63;
  margin-bottom: 4mm;
}}
.toc-grid {{ display: flex; flex-wrap: wrap; gap: 3mm 8mm; }}
.toc-item {{
  width: calc(50% - 4mm);
  display: flex;
  align-items: baseline;
  gap: 3mm;
  padding-bottom: 2mm;
  border-bottom: 1px solid #000;
}}
.toc-item .n {{
  font-size: 9pt; font-weight: 700;
  letter-spacing: 0.12em; color: #DC6A63; white-space: nowrap;
}}
.toc-item .t {{ font-size: 10pt; font-weight: 600; color: #000; line-height: 1.2; }}

/* ══ SECTION TYPOGRAPHY ══ */
.section-num {{
  font-size: 9pt; font-weight: 700;
  letter-spacing: 0.22em; text-transform: uppercase;
  color: #DC6A63; margin-bottom: 4mm;
}}
h1.section-title {{
  font-size: 28pt; font-weight: 700;
  letter-spacing: -0.025em; line-height: 1.02;
  margin: 0 0 4mm;
}}
.section-lede {{
  font-size: 12pt; font-weight: 400;
  line-height: 1.4; color: #000;
  max-width: 150mm; margin: 0 0 10mm;
  letter-spacing: -0.005em;
}}
.section-lede em {{ font-style: normal; color: #DC6A63; font-weight: 500; }}
.page p {{ margin: 0 0 3.5mm; line-height: 1.6; font-size: 10.5pt; }}
.page h2 {{
  font-size: 15pt; font-weight: 700;
  letter-spacing: -0.015em; margin: 0 0 3mm; line-height: 1.15;
}}
.page h3 {{
  font-size: 11pt; font-weight: 700;
  letter-spacing: -0.005em; margin: 0 0 2mm;
}}

/* ══ STAGES (approach page) ══ */
.stages {{ display: flex; gap: 8mm; margin-top: 2mm; }}
.stage {{
  flex: 1; border: 1px solid #000;
  padding: 8mm; display: flex; flex-direction: column;
}}
.stage__num {{
  font-size: 52pt; font-weight: 700;
  letter-spacing: -0.05em; line-height: 0.85;
  color: #DC6A63; margin: 0 0 4mm;
}}
.stage__label {{
  font-size: 8.5pt; letter-spacing: 0.22em;
  text-transform: uppercase; font-weight: 700;
  color: #000; margin-bottom: 2mm;
}}
.stage__name {{
  font-size: 17pt; font-weight: 700;
  letter-spacing: -0.02em; line-height: 1.05;
  margin: 0 0 5mm; padding-bottom: 4mm;
  border-bottom: 1px solid #000;
}}
.stage p {{ font-size: 10pt; line-height: 1.55; margin: 0 0 3mm; }}
.stage .pullout {{
  margin-top: auto; padding-top: 5mm;
  border-top: 1px solid #000;
  font-size: 9pt; letter-spacing: 0.1em;
  text-transform: uppercase; font-weight: 700;
  color: #DC6A63; line-height: 1.35;
}}
.both-matter {{
  margin-top: 10mm; padding-top: 7mm;
  border-top: 2px solid #000;
  display: flex; gap: 8mm;
}}
.both-matter__heading {{
  width: 50mm; flex-shrink: 0;
  font-size: 13pt; font-weight: 700;
  letter-spacing: -0.005em; line-height: 1.2;
}}
.both-matter__heading .coral {{ color: #DC6A63; }}
.both-matter__body p {{ font-size: 10.5pt; line-height: 1.6; margin: 0 0 3mm; }}
.both-matter__emph {{ color: #DC6A63; font-weight: 500; }}

/* ══ CHANGES (what I changed) ══ */
.changes {{ display: flex; flex-direction: column; }}
.change {{
  display: flex; gap: 8mm;
  padding: 7mm 0; border-top: 1px solid #000;
  align-items: flex-start;
}}
.change:last-child {{ border-bottom: 1px solid #000; }}
.change__num {{
  width: 28mm; flex-shrink: 0;
  font-size: 42pt; font-weight: 700;
  letter-spacing: -0.04em; line-height: 0.9;
  color: #DC6A63;
}}
.change__body h3 {{
  font-size: 14pt; font-weight: 700;
  letter-spacing: -0.015em; line-height: 1.15;
  margin: 1mm 0 3mm;
}}
.change__body p {{ font-size: 10.5pt; line-height: 1.6; margin: 0; max-width: 130mm; }}

/* ══ ASSESSMENT (gap report) ══ */
.assessment {{ display: flex; flex-direction: column; gap: 6mm; }}
.assess {{ border: 1px solid #000; display: flex; flex-direction: row; }}
.assess__rail {{
  width: 8mm; flex-shrink: 0;
}}
.assess__body {{ padding: 7mm 8mm; flex: 1; }}
.assess__head {{
  display: flex; justify-content: space-between;
  align-items: baseline; gap: 6mm;
  padding-bottom: 3mm; margin-bottom: 4mm;
  border-bottom: 1px solid #000;
}}
.assess__index {{
  font-size: 9pt; font-weight: 700;
  letter-spacing: 0.22em; text-transform: uppercase;
  color: #DC6A63;
}}
.assess__tag {{
  font-size: 8pt; font-weight: 700;
  letter-spacing: 0.2em; text-transform: uppercase;
  padding: 1mm 3mm; border: 1px solid #000; white-space: nowrap;
}}
.assess__title {{
  font-size: 14pt; font-weight: 700;
  letter-spacing: -0.015em; line-height: 1.15; margin: 0 0 3mm;
}}
.assess p {{ font-size: 10.5pt; line-height: 1.6; margin: 0; }}
.assess-closer {{
  margin-top: 10mm; padding-top: 7mm;
  border-top: 2px solid #000;
  font-size: 11.5pt; line-height: 1.5;
  letter-spacing: -0.005em; max-width: 160mm;
}}
.assess-closer .coral {{ color: #DC6A63; font-weight: 600; }}

/* ══ CLOSER / THANK YOU ══ */
.closer__lede {{
  font-size: 15pt; line-height: 1.35;
  font-weight: 500; letter-spacing: -0.01em;
  max-width: 155mm; margin: 0 0 8mm;
}}
.closer__lede .coral {{ color: #DC6A63; }}
.signoff {{
  padding: 9mm 0 10mm;
  border-top: 1px solid #000; border-bottom: 1px solid #000;
  margin: 4mm 0 10mm;
  display: flex; flex-direction: column; gap: 5mm;
}}
.signoff__kicker {{
  font-size: 9pt; font-weight: 700;
  letter-spacing: 0.22em; text-transform: uppercase; color: #DC6A63;
}}
.signoff__who .name {{ font-size: 12pt; font-weight: 700; margin: 0 0 1mm; }}
.signoff__who .role {{
  font-size: 9pt; font-weight: 600;
  letter-spacing: 0.08em; text-transform: uppercase; color: #DC6A63;
}}
.next-steps-label {{
  font-size: 9pt; font-weight: 700;
  letter-spacing: 0.22em; text-transform: uppercase;
  color: #DC6A63; margin-bottom: 4mm;
}}
.next-step {{
  display: flex; gap: 6mm;
  padding: 5mm 0; border-top: 1px solid #000;
  align-items: flex-start;
}}
.next-step:last-child {{ border-bottom: 1px solid #000; }}
.next-step__dot {{
  width: 3mm; height: 3mm; border-radius: 50%;
  background: #DC6A63; flex-shrink: 0; margin-top: 4pt;
}}
.next-step__body h4 {{ font-size: 11pt; font-weight: 700; margin: 0 0 1mm; }}
.next-step__body p {{ font-size: 10pt; line-height: 1.55; margin: 0; }}

/* ── Print / WeasyPrint ── */
@media print {{
  html, body {{ background: white; }}
  .doc {{ padding: 0; gap: 0; }}
  .page {{ box-shadow: none; }}
}}
@page {{ size: A4; margin: 0; }}
</style>
</head>
<body>
<div class="doc">

<!-- ══════════════════════════════════════════════════════════════
     PAGE 1 — COVER
     ══════════════════════════════════════════════════════════════ -->
<section class="page cover">
  <div class="cover__top">
    {logo_html}
    <div class="cover__meta">
      <span class="coral">CV Optimisation Report</span><br>
      Prepared {date_str}
    </div>
  </div>

  <div class="cover__body">
    <div class="cover__eyebrow">CV Optimisation Report</div>
    <h1 class="cover__title">
      Your CV<span class="comma-wink">,</span><br>
      rebuilt to<br>
      be <span class="coral">shortlisted</span>.
    </h1>
    <p class="cover__subtitle">
      The structure, the language, the framing of your achievements, and the
      keywords that carry you through automated screening, and in front of
      Hiring Managers. <strong>All of it, rebuilt.</strong>
    </p>

    <div class="cover__client">
      <div>
        <span class="label">Prepared for</span>
        <span class="value">{name}<small>{tagline}</small></span>
      </div>
      <div>
        <span class="label">Prepared by</span>
        <span class="value">Brendan Johns<small>Career Coach, Dear Hiring Manager</small></span>
      </div>
      <div>
        <span class="label">Turnaround</span>
        <span class="value">24 – 48 hours<small>Delivered alongside your optimised .docx</small></span>
      </div>
    </div>
  </div>

  <div class="cover__bottom">
    <span>Dear Hiring Manager<span class="comma-wink">,</span></span>
    <span class="tag">Career Coaching</span>
  </div>
</section>

<!-- ══════════════════════════════════════════════════════════════
     PAGE 2 — WELCOME
     ══════════════════════════════════════════════════════════════ -->
<section class="page">
  <div class="page__header">
    <span class="lhs">CV Optimisation Report</span>
    <span class="rhs">{name}</span>
  </div>

  <div class="welcome__hero">
    <div class="kicker">— A note to open with</div>
    <h1>Your optimised CV is <span class="coral" style="color:#DC6A63;">ready</span>.</h1>
  </div>

  <div class="welcome__body">
    <div class="meta-col">
      <div class="group">
        <span class="label">Client</span>
        <span class="value">{name}</span>
      </div>
      <div class="group">
        <span class="label">Service</span>
        <span class="value">CV Optimisation</span>
      </div>
      <div class="group">
        <span class="label">Delivered</span>
        <span class="value">{date_str}</span>
      </div>
      <div class="group">
        <span class="label">Format</span>
        <span class="value">.docx (ATS-ready)</span>
      </div>
      <div class="group">
        <span class="label">In this report</span>
        <span class="value">Approach, changes,<br>honest assessment,<br>what's next.</span>
      </div>
    </div>

    <div class="welcome__prose">
      <p class="big">Your CV has been optimised.</p>
      <p>You have done the hard work to get here. This document finally reflects it properly.</p>
      <p>This report is the thinking behind it. Every change we made to your CV is laid out, along with an honest assessment of what is strong and what still needs your attention before you start applying.</p>

      <div class="welcome__toc">
        <div class="welcome__toc-label">Contents</div>
        <div class="toc-grid">
          <div class="toc-item"><span class="n">01</span><span class="t">How we approach CV optimisation</span></div>
          <div class="toc-item"><span class="n">02</span><span class="t">What I changed, and why</span></div>
          <div class="toc-item"><span class="n">03</span><span class="t">My honest assessment</span></div>
          <div class="toc-item"><span class="n">04</span><span class="t">Thank you, and what's next</span></div>
        </div>
      </div>
    </div>
  </div>

  <div class="page__footer">
    <span>Dear Hiring Manager<span class="comma-wink">,</span></span>
    <span>Confidential — For {name}</span>
    <span>Page <span class="page-no">02</span></span>
  </div>
</section>

<!-- ══════════════════════════════════════════════════════════════
     PAGE 3 — HOW WE APPROACH CV OPTIMISATION
     ══════════════════════════════════════════════════════════════ -->
<section class="page">
  <div class="page__header">
    <span class="lhs">01 &nbsp;·&nbsp; How we approach CV optimisation</span>
    <span class="rhs">{name}</span>
  </div>

  <div class="section-num">Section 01</div>
  <h1 class="section-title">How we approach<br>CV optimisation<span class="comma-wink" style="font-size:28pt;">,</span></h1>
  <p class="section-lede">What we consider, and why it matters. Every CV we optimise is evaluated against <em>two distinct stages</em> of the hiring process. Both matter. Failing either one ends your application before it has begun.</p>

  <div class="stages">
    <div class="stage">
      <div class="stage__num">01</div>
      <div class="stage__label">Stage One</div>
      <div class="stage__name">The Technology</div>
      <p>Before a recruiter reads a single word, your CV is processed by an Applicant Tracking System. ATS software parses your document and scores it against the job specification. If the right signals are not present, the CV is rejected automatically. No human sees it.</p>
      <p>Those signals include formatting, keywords, job title alignment, section headings, achievement framing, and industry-specific terminology. Each of these has been addressed in your optimised CV, because getting any one of them wrong is enough to trigger an automated rejection.</p>
      <div class="pullout">Your CV has been saved as a .docx — the standard format for ATS submissions.</div>
    </div>
    <div class="stage">
      <div class="stage__num">02</div>
      <div class="stage__label">Stage Two</div>
      <div class="stage__name">The Human</div>
      <p>If your CV clears the ATS stage, it reaches a recruiter or hiring manager. Research consistently shows that initial CV decisions are made within the first few seconds of opening a document. In that window, the reader is scanning for one thing: evidence that this person can do what we need.</p>
      <p>To make sure your CV holds attention beyond that first scan, every role focuses on results and impact, your career story is easy to follow, and the language and skills match the roles you are targeting.</p>
      <div class="pullout">A CV that reads well but fails ATS never reaches a human at all.</div>
    </div>
  </div>

  <div class="both-matter">
    <div class="both-matter__heading">Why <span class="coral">both</span><br>stages matter.</div>
    <div class="both-matter__body">
      <p>A CV that passes ATS but reads poorly to a human does not get an interview. A CV that reads well but fails ATS never reaches a human at all. <span class="both-matter__emph">Every decision made in your optimised CV — formatting, structure, language, and framing — has been made with both stages in mind.</span></p>
      <p>The goal is straightforward: to get you in front of the right person, face to face, where you can do what no CV can do. Bring your story to life.</p>
    </div>
  </div>

  <div class="page__footer">
    <span>Dear Hiring Manager<span class="comma-wink">,</span></span>
    <span>Confidential — For {name}</span>
    <span>Page <span class="page-no">03</span></span>
  </div>
</section>

<!-- ══════════════════════════════════════════════════════════════
     PAGE 4 — WHAT I CHANGED
     ══════════════════════════════════════════════════════════════ -->
<section class="page">
  <div class="page__header">
    <span class="lhs">02 &nbsp;·&nbsp; What I changed</span>
    <span class="rhs">{name}</span>
  </div>

  <div class="section-num">Section 02</div>
  <h1 class="section-title">What I changed<span class="comma-wink" style="font-size:28pt;">,</span><br>and why.</h1>
  <p class="section-lede">Every change was <em>deliberate</em>. Here is the thinking behind each one — the edits that do the heaviest lifting in your new CV.</p>

  <div class="changes">
    {change_items_html}
  </div>

  <div class="page__footer">
    <span>Dear Hiring Manager<span class="comma-wink">,</span></span>
    <span>Confidential — For {name}</span>
    <span>Page <span class="page-no">04</span></span>
  </div>
</section>

<!-- ══════════════════════════════════════════════════════════════
     PAGE 5 — MY HONEST ASSESSMENT
     ══════════════════════════════════════════════════════════════ -->
<section class="page">
  <div class="page__header">
    <span class="lhs">03 &nbsp;·&nbsp; Honest assessment</span>
    <span class="rhs">{name}</span>
  </div>

  <div class="section-num">Section 03</div>
  <h1 class="section-title">My honest<br>assessment<span class="comma-wink" style="font-size:28pt;">,</span></h1>
  <p class="section-lede">The CV is stronger. These are the things worth knowing as you head into your search — <em>ordered by the impact they will have on your interview rate.</em></p>

  <div class="assessment">
    {assess_items_html}
  </div>

  <div class="assess-closer">
    Addressing even one or two of these points before you start applying will put you <span class="coral">meaningfully ahead</span>. The changes are straightforward. The difference they make to your results will not be.
  </div>

  <div class="page__footer">
    <span>Dear Hiring Manager<span class="comma-wink">,</span></span>
    <span>Confidential — For {name}</span>
    <span>Page <span class="page-no">05</span></span>
  </div>
</section>

<!-- ══════════════════════════════════════════════════════════════
     PAGE 6 — THANK YOU
     ══════════════════════════════════════════════════════════════ -->
<section class="page">
  <div class="page__header">
    <span class="lhs">04 &nbsp;·&nbsp; Thank you, and what's next</span>
    <span class="rhs">{name}</span>
  </div>

  <div class="section-num">Section 04</div>
  <h1 class="section-title">Thank you<span class="comma-wink" style="font-size:28pt;">,</span></h1>

  <p class="closer__lede">
    It is a privilege to work on something that matters this much. Helping people
    navigate a system that was not built in their favour is why we do this.
    We hope your optimised CV opens the doors it deserves to. Thank you for
    choosing <span class="coral">Dear Hiring Manager</span>.
  </p>

  <div class="signoff">
    <div class="signoff__kicker">— With thanks</div>
    {sig_html}
    <div class="signoff__who">
      <div class="name">Brendan Johns</div>
      <div class="role">Career Coach · Dear Hiring Manager</div>
    </div>
  </div>

  <div class="next-steps-label">When you're ready to go further</div>

  <div class="next-step">
    <div class="next-step__dot"></div>
    <div class="next-step__body">
      <h4>LinkedIn Profile Optimisation</h4>
      <p>Aligning your LinkedIn presence with your optimised CV so every touchpoint tells the same story. Recruiters check both. They need to match.</p>
    </div>
  </div>
  <div class="next-step">
    <div class="next-step__dot"></div>
    <div class="next-step__body">
      <h4>Job Search Strategy</h4>
      <p>A structured approach to targeting the right roles, in the right organisations, in the right way. More signal. Less noise.</p>
    </div>
  </div>
  <div class="next-step">
    <div class="next-step__dot"></div>
    <div class="next-step__body">
      <h4>Interview Preparation and Mock Interviews</h4>
      <p>When the CV gets you through the door, you need to be ready for what comes next. We work with you to prepare, sharpen your answers, and walk in with confidence.</p>
    </div>
  </div>

  <div class="page__footer">
    <span>Dear Hiring Manager<span class="comma-wink">,</span></span>
    <span>www.DearHiringManager.careers</span>
    <span>Page <span class="page-no">06</span></span>
  </div>
</section>

</div>
</body>
</html>'''
