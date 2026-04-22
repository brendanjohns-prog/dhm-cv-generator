"""
DHM CV Optimisation Report — HTML Generator (xhtml2pdf compatible)
------------------------------------------------------------------
Produces a self-contained HTML string using table-based layout,
ready for xhtml2pdf -> PDF conversion. No flexbox, no writing-mode.
"""

import base64
import os
import re
from datetime import datetime

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
    """Extract [HIGH PRIORITY] / [MEDIUM PRIORITY] tag. Returns (clean_title, 'high'|'medium')."""
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


def build_report_html(cv_data):
    """
    Generate the complete HTML string for one client's CV Optimisation Report.
    Uses table-based layout for xhtml2pdf compatibility.
    """
    name      = _esc(cv_data.get('name', 'Client'))
    tagline   = _esc(cv_data.get('tagline', ''))
    changelog = cv_data.get('changelog', [])
    gap_report = cv_data.get('gap_report', [])
    date_str  = datetime.now().strftime('%B %Y')

    logo_src = _embed('DHM_App_Logo.png')
    sig_src  = _embed('DHM_Report_Signature_V3.png')

    logo_html = (
        f'<img src="{logo_src}" alt="Dear Hiring Manager" style="height:22mm;width:auto;">'
        if logo_src else
        '<span style="font-size:16pt;font-weight:bold;">Dear Hiring Manager</span>'
    )
    sig_html = (
        f'<img src="{sig_src}" alt="Brendan Johns" style="width:90mm;height:auto;">'
        if sig_src else ''
    )

    # ── Changelog rows ────────────────────────────────────────────────────────
    change_rows = ''
    for i, item in enumerate(changelog, 1):
        t = _esc(item.get('title', ''))
        p = _esc(item.get('text', ''))
        change_rows += f'''
        <tr>
          <td style="width:18mm;vertical-align:top;padding:5mm 5mm 5mm 0;border-top:1px solid #000;">
            <span style="font-size:34pt;font-weight:700;color:#DC6A63;line-height:1;">{i:02d}</span>
          </td>
          <td style="vertical-align:top;padding:5mm 0;border-top:1px solid #000;">
            <p style="font-size:13pt;font-weight:700;margin:0 0 2mm 0;">{t}</p>
            <p style="font-size:10pt;line-height:1.55;margin:0;">{p}</p>
          </td>
        </tr>'''

    # ── Assessment rows ───────────────────────────────────────────────────────
    assess_rows = ''
    for i, item in enumerate(gap_report, 1):
        raw_title  = item.get('title', '')
        body_text  = _esc(item.get('text', ''))
        title, priority = _parse_priority(raw_title)
        title      = _esc(title)
        label      = 'High Priority' if priority == 'high' else 'Medium Priority'
        rail_bg    = '#DC6A63' if priority == 'high' else '#000000'
        tag_style  = (
            'background:#DC6A63;color:#fff;border:1px solid #DC6A63;padding:1mm 3mm;'
            if priority == 'high' else
            'border:1px solid #000;padding:1mm 3mm;'
        )
        assess_rows += f'''
        <tr>
          <td style="padding:0 0 5mm 0;">
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #000;">
              <tr>
                <td style="width:8mm;background:{rail_bg};">&nbsp;</td>
                <td style="padding:6mm 7mm;">
                  <table width="100%" cellpadding="0" cellspacing="0"
                         style="border-bottom:1px solid #000;padding-bottom:3mm;margin-bottom:3mm;">
                    <tr>
                      <td>
                        <span style="font-size:8pt;font-weight:700;letter-spacing:0.15em;
                                     text-transform:uppercase;color:#DC6A63;">Item {i:02d}</span>
                      </td>
                      <td align="right">
                        <span style="font-size:7.5pt;font-weight:700;letter-spacing:0.12em;
                                     text-transform:uppercase;{tag_style}">{label}</span>
                      </td>
                    </tr>
                  </table>
                  <p style="font-size:13pt;font-weight:700;margin:0 0 3mm 0;">{title}</p>
                  <p style="font-size:10pt;line-height:1.55;margin:0;">{body_text}</p>
                </td>
              </tr>
            </table>
          </td>
        </tr>'''

    # ── Next steps ────────────────────────────────────────────────────────────
    next_steps_data = [
        ('LinkedIn Profile Optimisation',
         'Aligning your LinkedIn presence with your optimised CV so every touchpoint tells the same story. Recruiters check both. They need to match.'),
        ('Job Search Strategy',
         'A structured approach to targeting the right roles, in the right organisations, in the right way. More signal. Less noise.'),
        ('Interview Preparation and Mock Interviews',
         'When the CV gets you through the door, you need to be ready for what comes next. We work with you to prepare, sharpen your answers, and walk in with confidence.'),
    ]
    next_step_rows = ''
    for ns_title, ns_body in next_steps_data:
        next_step_rows += f'''
        <tr>
          <td style="width:6mm;vertical-align:top;padding:4mm 4mm 4mm 0;border-top:1px solid #000;">
            <span style="color:#DC6A63;font-size:12pt;">&#x25CF;</span>
          </td>
          <td style="vertical-align:top;padding:4mm 0;border-top:1px solid #000;">
            <p style="font-size:11pt;font-weight:700;margin:0 0 1mm 0;">{ns_title}</p>
            <p style="font-size:10pt;line-height:1.5;margin:0;">{ns_body}</p>
          </td>
        </tr>'''

    # ── Helpers ───────────────────────────────────────────────────────────────
    def page_header(section, n):
        return f'''
        <table width="100%" cellpadding="0" cellspacing="0"
               style="border-bottom:1px solid #000;margin-bottom:8mm;padding-bottom:4mm;">
          <tr>
            <td style="font-size:8pt;font-weight:600;letter-spacing:0.08em;
                       text-transform:uppercase;">{section}</td>
            <td align="right" style="font-size:8pt;font-weight:600;letter-spacing:0.08em;
                                     text-transform:uppercase;color:#DC6A63;">{n}</td>
          </tr>
        </table>'''

    def page_footer(page_num, n, right_text=None):
        right = right_text or f'Confidential &mdash; For {n}'
        return f'''
        <table width="100%" cellpadding="0" cellspacing="0"
               style="border-top:1px solid #000;margin-top:8mm;padding-top:4mm;">
          <tr>
            <td style="font-size:8pt;font-weight:500;letter-spacing:0.06em;
                       text-transform:uppercase;">Dear Hiring Manager,</td>
            <td align="center" style="font-size:8pt;">{right}</td>
            <td align="right" style="font-size:8pt;font-weight:700;
                                     color:#DC6A63;">Page {page_num:02d}</td>
          </tr>
        </table>'''

    # ══════════════════════════════════════════════════════════════════════════
    return f'''<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8"/>
<title>CV Optimisation Report &mdash; {name}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10pt;
    color: #000;
    line-height: 1.5;
  }}
  @page {{ size: A4; margin: 20mm 22mm; }}
  .page {{ page-break-before: always; }}
  p {{ margin: 0 0 3mm 0; }}
  h1 {{ font-size: 26pt; font-weight: 700; margin: 0 0 4mm 0; line-height: 1.05; }}
</style>
</head>
<body>

<!-- ══════════════════════════════════════════════════════════
     PAGE 1 — COVER
     ══════════════════════════════════════════════════════════ -->
<table width="100%" cellpadding="0" cellspacing="0"
       style="border-bottom:1px solid #000;padding-bottom:5mm;margin-bottom:10mm;">
  <tr>
    <td style="vertical-align:bottom;">{logo_html}</td>
    <td align="right" style="vertical-align:bottom;font-size:8pt;font-weight:600;
                              letter-spacing:0.1em;text-transform:uppercase;">
      <span style="color:#DC6A63;">CV Optimisation Report</span><br>
      Prepared {date_str}
    </td>
  </tr>
</table>

<p style="font-size:8.5pt;font-weight:700;letter-spacing:0.22em;text-transform:uppercase;
          color:#DC6A63;margin:0 0 6mm 0;">&#x2014;&nbsp; CV Optimisation Report</p>

<h1 style="font-size:50pt;font-weight:700;line-height:0.95;letter-spacing:-0.03em;margin:0 0 8mm 0;">
  Your CV,<br>rebuilt to<br>be <span style="color:#DC6A63;">shortlisted</span>.
</h1>

<p style="font-size:12pt;line-height:1.4;margin:0 0 10mm 0;max-width:140mm;">
  The structure, the language, the framing of your achievements, and the keywords that carry
  you through automated screening, and in front of Hiring Managers.
  <strong>All of it, rebuilt.</strong>
</p>

<table width="100%" cellpadding="0" cellspacing="0"
       style="border-top:1px solid #000;border-bottom:1px solid #000;
              padding:5mm 0;margin:0 0 10mm 0;">
  <tr>
    <td style="width:33%;padding-right:5mm;vertical-align:top;">
      <span style="font-size:7.5pt;font-weight:700;letter-spacing:0.18em;
                   text-transform:uppercase;color:#DC6A63;">Prepared for</span><br>
      <span style="font-size:11pt;font-weight:600;">{name}</span><br>
      <span style="font-size:9pt;">{tagline}</span>
    </td>
    <td style="width:33%;padding:0 5mm;border-left:1px solid #000;vertical-align:top;">
      <span style="font-size:7.5pt;font-weight:700;letter-spacing:0.18em;
                   text-transform:uppercase;color:#DC6A63;">Prepared by</span><br>
      <span style="font-size:11pt;font-weight:600;">Brendan Johns</span><br>
      <span style="font-size:9pt;">Career Coach, Dear Hiring Manager</span>
    </td>
    <td style="width:33%;padding-left:5mm;border-left:1px solid #000;vertical-align:top;">
      <span style="font-size:7.5pt;font-weight:700;letter-spacing:0.18em;
                   text-transform:uppercase;color:#DC6A63;">Turnaround</span><br>
      <span style="font-size:11pt;font-weight:600;">24 &ndash; 48 hours</span><br>
      <span style="font-size:9pt;">Delivered alongside your optimised .docx</span>
    </td>
  </tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0"
       style="border-top:1px solid #000;padding-top:5mm;">
  <tr>
    <td style="font-size:8.5pt;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;">
      Dear Hiring Manager,</td>
    <td align="right" style="font-size:8.5pt;font-weight:600;letter-spacing:0.1em;
                              text-transform:uppercase;color:#DC6A63;">Career Coaching</td>
  </tr>
</table>


<!-- ══════════════════════════════════════════════════════════
     PAGE 2 — WELCOME
     ══════════════════════════════════════════════════════════ -->
<div class="page">
  {page_header('CV Optimisation Report', name)}

  <p style="font-size:8.5pt;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
            color:#DC6A63;margin:0 0 3mm 0;">&mdash; A note to open with</p>
  <h1 style="font-size:28pt;margin:0 0 8mm 0;">
    Your optimised CV is <span style="color:#DC6A63;">ready</span>.
  </h1>

  <table width="100%" cellpadding="0" cellspacing="0"
         style="border-top:1px solid #000;padding-top:6mm;">
    <tr>
      <td style="width:52mm;vertical-align:top;padding-right:8mm;">
        <p style="font-size:7.5pt;font-weight:700;letter-spacing:0.15em;
                  text-transform:uppercase;color:#DC6A63;margin:0 0 1mm 0;">Client</p>
        <p style="font-size:10pt;font-weight:500;margin:0 0 4mm 0;">{name}</p>
        <p style="font-size:7.5pt;font-weight:700;letter-spacing:0.15em;
                  text-transform:uppercase;color:#DC6A63;margin:0 0 1mm 0;">Service</p>
        <p style="font-size:10pt;font-weight:500;margin:0 0 4mm 0;">CV Optimisation</p>
        <p style="font-size:7.5pt;font-weight:700;letter-spacing:0.15em;
                  text-transform:uppercase;color:#DC6A63;margin:0 0 1mm 0;">Delivered</p>
        <p style="font-size:10pt;font-weight:500;margin:0 0 4mm 0;">{date_str}</p>
        <p style="font-size:7.5pt;font-weight:700;letter-spacing:0.15em;
                  text-transform:uppercase;color:#DC6A63;margin:0 0 1mm 0;">Format</p>
        <p style="font-size:10pt;font-weight:500;margin:0 0 4mm 0;">.docx (ATS-ready)</p>
        <p style="font-size:7.5pt;font-weight:700;letter-spacing:0.15em;
                  text-transform:uppercase;color:#DC6A63;margin:0 0 1mm 0;">In this report</p>
        <p style="font-size:10pt;font-weight:500;margin:0;">
          Approach, changes,<br>honest assessment,<br>what&rsquo;s next.</p>
      </td>
      <td style="vertical-align:top;">
        <p style="font-size:12pt;font-weight:500;margin:0 0 4mm 0;">
          Your CV has been optimised.</p>
        <p style="margin:0 0 3mm 0;">
          You have done the hard work to get here. This document finally reflects it properly.</p>
        <p style="margin:0 0 8mm 0;">
          This report is the thinking behind it. Every change we made to your CV is laid out,
          along with an honest assessment of what is strong and what still needs your attention
          before you start applying.</p>

        <p style="font-size:8.5pt;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
                  color:#DC6A63;margin:0 0 4mm 0;">Contents</p>
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="width:50%;padding:2mm 4mm 2mm 0;border-bottom:1px solid #000;">
              <span style="font-size:8.5pt;font-weight:700;color:#DC6A63;">01&nbsp;&nbsp;</span>
              <span style="font-size:10pt;font-weight:600;">How we approach CV optimisation</span>
            </td>
            <td style="width:50%;padding:2mm 0 2mm 4mm;border-bottom:1px solid #000;
                       border-left:1px solid #000;">
              <span style="font-size:8.5pt;font-weight:700;color:#DC6A63;">&nbsp;&nbsp;02&nbsp;&nbsp;</span>
              <span style="font-size:10pt;font-weight:600;">What I changed, and why</span>
            </td>
          </tr>
          <tr>
            <td style="padding:2mm 4mm 2mm 0;border-bottom:1px solid #000;">
              <span style="font-size:8.5pt;font-weight:700;color:#DC6A63;">03&nbsp;&nbsp;</span>
              <span style="font-size:10pt;font-weight:600;">My honest assessment</span>
            </td>
            <td style="padding:2mm 0 2mm 4mm;border-bottom:1px solid #000;
                       border-left:1px solid #000;">
              <span style="font-size:8.5pt;font-weight:700;color:#DC6A63;">&nbsp;&nbsp;04&nbsp;&nbsp;</span>
              <span style="font-size:10pt;font-weight:600;">Thank you, and what&rsquo;s next</span>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

  {page_footer(2, name)}
</div>


<!-- ══════════════════════════════════════════════════════════
     PAGE 3 — APPROACH
     ══════════════════════════════════════════════════════════ -->
<div class="page">
  {page_header('01 &middot; How we approach CV optimisation', name)}

  <p style="font-size:8.5pt;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
            color:#DC6A63;margin:0 0 2mm 0;">Section 01</p>
  <h1 style="margin:0 0 3mm 0;">How we approach<br>CV optimisation,</h1>
  <p style="font-size:11pt;line-height:1.4;margin:0 0 7mm 0;max-width:150mm;">
    What we consider, and why it matters. Every CV we optimise is evaluated against
    <span style="color:#DC6A63;font-weight:500;">two distinct stages</span> of the hiring process.
    Both matter. Failing either one ends your application before it has begun.</p>

  <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 8mm 0;">
    <tr>
      <td style="width:49%;vertical-align:top;border:1px solid #000;padding:6mm;">
        <p style="font-size:38pt;font-weight:700;color:#DC6A63;line-height:0.9;margin:0 0 2mm 0;">01</p>
        <p style="font-size:8pt;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
                  margin:0 0 1mm 0;">Stage One</p>
        <p style="font-size:15pt;font-weight:700;border-bottom:1px solid #000;
                  padding-bottom:4mm;margin:0 0 4mm 0;">The Technology</p>
        <p style="font-size:10pt;margin:0 0 3mm 0;">
          Before a recruiter reads a single word, your CV is processed by an Applicant Tracking
          System. ATS software parses your document and scores it against the job specification.
          If the right signals are not present, the CV is rejected automatically. No human sees it.</p>
        <p style="font-size:10pt;margin:0 0 4mm 0;">
          Those signals include formatting, keywords, job title alignment, section headings,
          achievement framing, and industry-specific terminology. Each of these has been
          addressed in your optimised CV.</p>
        <p style="font-size:8.5pt;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
                  color:#DC6A63;border-top:1px solid #000;padding-top:4mm;margin:0;">
          Your CV has been saved as a .docx &mdash; the standard format for ATS submissions.</p>
      </td>
      <td style="width:2%;"></td>
      <td style="width:49%;vertical-align:top;border:1px solid #000;padding:6mm;">
        <p style="font-size:38pt;font-weight:700;color:#DC6A63;line-height:0.9;margin:0 0 2mm 0;">02</p>
        <p style="font-size:8pt;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
                  margin:0 0 1mm 0;">Stage Two</p>
        <p style="font-size:15pt;font-weight:700;border-bottom:1px solid #000;
                  padding-bottom:4mm;margin:0 0 4mm 0;">The Human</p>
        <p style="font-size:10pt;margin:0 0 3mm 0;">
          If your CV clears the ATS stage, it reaches a recruiter or hiring manager. Research
          consistently shows that initial CV decisions are made within the first few seconds
          of opening a document. In that window, the reader is scanning for one thing: evidence
          that this person can do what we need.</p>
        <p style="font-size:10pt;margin:0 0 4mm 0;">
          To make sure your CV holds attention beyond that first scan, every role focuses on
          results and impact, your career story is easy to follow, and the language matches
          the roles you are targeting.</p>
        <p style="font-size:8.5pt;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
                  color:#DC6A63;border-top:1px solid #000;padding-top:4mm;margin:0;">
          A CV that reads well but fails ATS never reaches a human at all.</p>
      </td>
    </tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0"
         style="border-top:2px solid #000;padding-top:6mm;">
    <tr>
      <td style="width:50mm;vertical-align:top;padding-right:8mm;">
        <p style="font-size:12pt;font-weight:700;margin:0;">
          Why <span style="color:#DC6A63;">both</span><br>stages matter.</p>
      </td>
      <td style="vertical-align:top;">
        <p style="font-size:10.5pt;margin:0 0 3mm 0;">
          A CV that passes ATS but reads poorly to a human does not get an interview. A CV that
          reads well but fails ATS never reaches a human at all.
          <span style="color:#DC6A63;font-weight:500;">Every decision made in your optimised CV
          has been made with both stages in mind.</span></p>
        <p style="font-size:10.5pt;margin:0;">
          The goal is straightforward: to get you in front of the right person, face to face,
          where you can do what no CV can do. Bring your story to life.</p>
      </td>
    </tr>
  </table>

  {page_footer(3, name)}
</div>


<!-- ══════════════════════════════════════════════════════════
     PAGE 4 — WHAT I CHANGED
     ══════════════════════════════════════════════════════════ -->
<div class="page">
  {page_header('02 &middot; What I changed', name)}

  <p style="font-size:8.5pt;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
            color:#DC6A63;margin:0 0 2mm 0;">Section 02</p>
  <h1 style="margin:0 0 3mm 0;">What I changed,<br>and why.</h1>
  <p style="font-size:11pt;line-height:1.4;margin:0 0 6mm 0;max-width:150mm;">
    Every change was <span style="color:#DC6A63;font-weight:500;">deliberate</span>.
    Here is the thinking behind each one.</p>

  <table width="100%" cellpadding="0" cellspacing="0">
    {change_rows}
    <tr>
      <td colspan="2" style="border-bottom:1px solid #000;height:1px;padding:0;"></td>
    </tr>
  </table>

  {page_footer(4, name)}
</div>


<!-- ══════════════════════════════════════════════════════════
     PAGE 5 — HONEST ASSESSMENT
     ══════════════════════════════════════════════════════════ -->
<div class="page">
  {page_header('03 &middot; Honest assessment', name)}

  <p style="font-size:8.5pt;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
            color:#DC6A63;margin:0 0 2mm 0;">Section 03</p>
  <h1 style="margin:0 0 3mm 0;">My honest<br>assessment,</h1>
  <p style="font-size:11pt;line-height:1.4;margin:0 0 6mm 0;max-width:150mm;">
    The CV is stronger. These are the things worth knowing as you head into your search &mdash;
    <span style="color:#DC6A63;font-weight:500;">ordered by the impact they will have on your
    interview rate.</span></p>

  <table width="100%" cellpadding="0" cellspacing="0">
    {assess_rows}
  </table>

  <p style="font-size:11pt;line-height:1.5;margin:6mm 0 0 0;max-width:160mm;">
    Addressing even one or two of these points before you start applying will put you
    <span style="color:#DC6A63;font-weight:600;">meaningfully ahead</span>. The changes are
    straightforward. The difference they make to your results will not be.</p>

  {page_footer(5, name)}
</div>


<!-- ══════════════════════════════════════════════════════════
     PAGE 6 — THANK YOU
     ══════════════════════════════════════════════════════════ -->
<div class="page">
  {page_header("04 &middot; Thank you, and what&rsquo;s next", name)}

  <p style="font-size:8.5pt;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
            color:#DC6A63;margin:0 0 2mm 0;">Section 04</p>
  <h1 style="margin:0 0 6mm 0;">Thank you,</h1>

  <p style="font-size:13pt;font-weight:500;line-height:1.4;margin:0 0 8mm 0;max-width:155mm;">
    It is a privilege to work on something that matters this much. Helping people navigate a
    system that was not built in their favour is why we do this. We hope your optimised CV
    opens the doors it deserves to. Thank you for choosing
    <span style="color:#DC6A63;">Dear Hiring Manager</span>.</p>

  <table width="100%" cellpadding="0" cellspacing="0"
         style="border-top:1px solid #000;border-bottom:1px solid #000;
                padding:8mm 0;margin:0 0 8mm 0;">
    <tr>
      <td>
        <p style="font-size:8.5pt;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
                  color:#DC6A63;margin:0 0 4mm 0;">&mdash; With thanks</p>
        {sig_html}
        <p style="font-size:12pt;font-weight:700;margin:4mm 0 1mm 0;">Brendan Johns</p>
        <p style="font-size:8.5pt;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;
                  color:#DC6A63;margin:0;">Career Coach &middot; Dear Hiring Manager</p>
      </td>
    </tr>
  </table>

  <p style="font-size:8.5pt;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
            color:#DC6A63;margin:0 0 4mm 0;">When you&rsquo;re ready to go further</p>

  <table width="100%" cellpadding="0" cellspacing="0">
    {next_step_rows}
    <tr>
      <td colspan="2" style="border-bottom:1px solid #000;height:1px;padding:0;"></td>
    </tr>
  </table>

  {page_footer(6, name, 'www.DearHiringManager.careers')}
</div>

</body>
</html>'''
