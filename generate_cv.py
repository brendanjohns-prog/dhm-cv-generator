#!/usr/bin/env python3
"""
DHM CV Optimisation Pipeline - Document Generator
Produces a consistently formatted .docx matching the DHM sample standard.
"""
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import re
import sys
import json


def add_horizontal_rule(paragraph, color='2E75B6'):
    """Add a bottom border to a paragraph to act as a horizontal rule."""
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def set_run_font(run, name='Calibri', size=11, bold=False, italic=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)


def add_section_heading(doc, text):
    """Add a styled section heading — navy text, blue rule beneath."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    set_run_font(run, size=11, bold=True, color=(31, 56, 100))  # #1F3864
    add_horizontal_rule(p, color='2E75B6')
    return p


def add_bullet(doc, text):
    """Add a properly formatted bullet point."""
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    run = p.add_run(str(text) if text is not None else "")
    set_run_font(run, size=10.5)
    return p


def add_numbered_item(doc, number, bold_title, text):
    """Add a numbered changelog or gap report item."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    # Number
    r1 = p.add_run(f"{number}. ")
    set_run_font(r1, size=10.5, bold=True)
    # Bold title
    r2 = p.add_run((str(bold_title) if bold_title is not None else "") + " — ")
    set_run_font(r2, size=10.5, bold=True)
    # Body text
    r3 = p.add_run(str(text) if text is not None else "")
    set_run_font(r3, size=10.5)
    return p


def render_summary(doc, summary_text):
    """
    Render the professional summary, splitting the closing 'Seeking...' sentence
    into its own paragraph for visual separation.
    """
    # First try splitting on double newlines (explicit paragraph breaks)
    parts = [p.strip() for p in summary_text.split('\n\n') if p.strip()]

    # Try single newlines if still one block
    if len(parts) == 1 and '\n' in summary_text:
        potential = [p.strip() for p in summary_text.split('\n') if p.strip()]
        if len(potential) > 1:
            parts = potential

    # Fallback: detect a closing career-objective sentence by keyword
    if len(parts) == 1:
        seeking_match = re.search(
            r'(?<=[.!?])\s+((?:Now\s+)?(?:[Ss]eeking|[Ll]ooking\s+for|[Tt]argeting\s+a|[Oo]pen\s+to)\b)',
            summary_text
        )
        if seeking_match:
            parts = [
                summary_text[:seeking_match.start()].strip(),
                summary_text[seeking_match.start():].strip()
            ]

    for i, part in enumerate(parts):
        if not part:
            continue
        p_sum = doc.add_paragraph()
        r_sum = p_sum.add_run(part)
        set_run_font(r_sum, size=10.5)
        p_sum.paragraph_format.space_before = Pt(0)
        # Extra space after the last paragraph only
        p_sum.paragraph_format.space_after = Pt(6) if i == len(parts) - 1 else Pt(4)


def build_cv_doc(cv_data, output_path):
    doc = Document()

    # === PAGE SETUP (A4, UK standard for CVs) ===
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)

    # === DOCUMENT HEADER — dark navy background, white text ===
    from docx.oxml import OxmlElement as OE2

    def add_paragraph_shading(paragraph, fill_hex):
        pPr = paragraph._p.get_or_add_pPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), fill_hex)
        pPr.append(shd)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    add_paragraph_shading(p, '1F3864')
    r = p.add_run("DEAR HIRING MANAGER — CV OPTIMISATION PIPELINE OUTPUT")
    set_run_font(r, size=11, bold=True, color=(255, 255, 255))

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_before = Pt(0)
    p2.paragraph_format.space_after = Pt(10)
    add_paragraph_shading(p2, '1F3864')
    r2 = p2.add_run(f"Output for: {cv_data['name']}  →  {cv_data['tagline']}")
    set_run_font(r2, size=9, italic=True, color=(200, 220, 240))

    # ===================================
    # SECTION 1 — REWRITTEN CV DRAFT
    # ===================================
    p_s1 = doc.add_paragraph()
    r_s1 = p_s1.add_run("SECTION 1 — REWRITTEN CV DRAFT")
    set_run_font(r_s1, size=11, bold=True, color=(46, 64, 87))
    r_s1.font.underline = True
    p_s1.paragraph_format.space_after = Pt(10)

    # Client Name — centred, large, dark
    p_name = doc.add_paragraph()
    p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_name = p_name.add_run(cv_data['name'])
    set_run_font(r_name, size=20, bold=True, color=(30, 30, 30))
    p_name.paragraph_format.space_before = Pt(10)
    p_name.paragraph_format.space_after = Pt(2)

    # Target Job Titles — centred, #2E75B6 blue
    p_titles = doc.add_paragraph()
    p_titles.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_titles = p_titles.add_run(cv_data['tagline'])
    set_run_font(r_titles, size=11, color=(46, 117, 182))
    p_titles.paragraph_format.space_after = Pt(2)

    # Contact Details — centred, grey
    p_contact = doc.add_paragraph()
    p_contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_contact = p_contact.add_run(cv_data['contact'])
    set_run_font(r_contact, size=10, color=(85, 85, 85))
    p_contact.paragraph_format.space_after = Pt(10)

    # PROFESSIONAL SUMMARY
    add_section_heading(doc, "PROFESSIONAL SUMMARY")
    render_summary(doc, cv_data.get('summary', ''))

    is_tech_role = cv_data.get('tech_role', False)

    def add_skills_section(doc, cv_data):
        add_section_heading(doc, "SKILLS")
        p_comp = doc.add_paragraph()
        p_comp.paragraph_format.space_before = Pt(4)
        p_comp.paragraph_format.space_after = Pt(6)
        r_comp = p_comp.add_run(cv_data['competencies'])
        set_run_font(r_comp, size=10.5, bold=False, color=(46, 117, 182))

    def add_technical_skills_section(doc, cv_data):
        if cv_data.get('technical_skills'):
            add_section_heading(doc, "TECHNICAL SKILLS")
            p_tech = doc.add_paragraph()
            r_tech = p_tech.add_run(cv_data['technical_skills'])
            set_run_font(r_tech, size=10.5)

    # Tech roles: Technical Skills comes before Skills and Work Experience
    if is_tech_role:
        add_technical_skills_section(doc, cv_data)
    add_skills_section(doc, cv_data)

    # WORK EXPERIENCE
    add_section_heading(doc, "WORK EXPERIENCE")
    for role in cv_data['employment']:
        # Role header: TITLE | COMPANY | DATES
        p_role = doc.add_paragraph()
        p_role.paragraph_format.space_before = Pt(8)
        p_role.paragraph_format.space_after = Pt(1)
        r_role = p_role.add_run(role['header'])
        set_run_font(r_role, size=10.5, bold=True)

        # Context line (italic)
        if role.get('context'):
            p_ctx = doc.add_paragraph()
            p_ctx.paragraph_format.space_before = Pt(1)
            p_ctx.paragraph_format.space_after = Pt(3)
            r_ctx = p_ctx.add_run(role['context'])
            set_run_font(r_ctx, size=10, italic=True, color=(80, 80, 80))

        # Achievement bullets
        for bullet in (role.get('bullets') or []):
            add_bullet(doc, bullet)

    # ADDITIONAL EXPERIENCE (formerly "Earlier Career" — broader ATS recognition)
    if cv_data.get('earlier_career'):
        add_section_heading(doc, "ADDITIONAL EXPERIENCE")
        for item in cv_data['earlier_career']:
            # Defensive: handle both plain strings and legacy dict format
            if isinstance(item, dict):
                title = item.get('title', '') or ''
                text = item.get('text', '') or ''
                line = title + (' — ' + text if text else '')
            else:
                line = str(item) if item is not None else ''
            if line:
                add_bullet(doc, line)

    # EDUCATION
    if cv_data.get('education'):
        add_section_heading(doc, "EDUCATION")
        for item in cv_data['education']:
            add_bullet(doc, item)

    # TECHNICAL SKILLS — at the bottom for non-tech roles
    if not is_tech_role:
        add_technical_skills_section(doc, cv_data)

    # Page break before changelog
    doc.add_paragraph().add_run("").font.size = Pt(1)
    from docx.oxml import OxmlElement as OE
    p_break = doc.add_paragraph()
    run_break = p_break.add_run()
    br = OE('w:br')
    br.set(qn('w:type'), 'page')
    run_break._r.append(br)

    # ===================================
    # SECTION 2 — STRATEGIC CHANGELOG
    # ===================================
    p_s2 = doc.add_paragraph()
    r_s2 = p_s2.add_run("SECTION 2 — STRATEGIC CHANGELOG")
    set_run_font(r_s2, size=11, bold=True, color=(46, 64, 87))
    r_s2.font.underline = True
    p_s2.paragraph_format.space_after = Pt(4)

    p_s2sub = doc.add_paragraph()
    r_s2sub = p_s2sub.add_run("What was changed from the original CV and why:")
    set_run_font(r_s2sub, size=10, italic=True, color=(80, 80, 80))
    p_s2sub.paragraph_format.space_after = Pt(8)

    for i, item in enumerate(cv_data['changelog'], 1):
        add_numbered_item(doc, i, item['title'], item['text'])

    # ===================================
    # SECTION 3 — GAP REPORT
    # ===================================
    doc.add_paragraph()
    p_s3 = doc.add_paragraph()
    r_s3 = p_s3.add_run("SECTION 3 — GAP REPORT")
    set_run_font(r_s3, size=11, bold=True, color=(46, 64, 87))
    r_s3.font.underline = True
    p_s3.paragraph_format.space_after = Pt(4)

    p_s3sub = doc.add_paragraph()
    r_s3sub = p_s3sub.add_run("Honest assessment of gaps between current profile and target role, with recommended actions:")
    set_run_font(r_s3sub, size=10, italic=True, color=(80, 80, 80))
    p_s3sub.paragraph_format.space_after = Pt(8)

    for i, item in enumerate(cv_data['gap_report'], 1):
        add_numbered_item(doc, i, item['title'], item['text'])

    doc.save(output_path)
    print(f"Saved: {output_path}")


if __name__ == '__main__':
    # === JAMES CARTER TEST DATA ===
    cv_data = {
        "tech_role": False,
        "name": "JAMES CARTER",
        "tagline": "Senior Marketing Manager | Head of Marketing | Demand Generation Lead",
        "contact": "07XXX XXXXXX  •  brendan.johns@dearhiringmanager.careers  •  London, UK",
        "summary": "A demand generation leader who built TechFlow's entire marketing function from scratch, generating £4.2M in attributed pipeline revenue — 67% year-on-year growth — and cutting customer acquisition cost by 31% in the process. Known for building data-driven marketing engines that align tightly with sales, with a consistent focus on pipeline impact over brand activity, recognised externally by a Best B2B Campaign win at the Northern Digital Awards 2020. Equally comfortable setting strategy and getting hands-on with execution, with deep expertise spanning B2B SaaS, Account-Based Marketing (ABM), paid acquisition, and organic growth across eight years in the sector.\n\nNow seeking a Head of Marketing or Senior Marketing Manager role with full ownership of pipeline strategy, team, and budget — bringing a proven ability to build from zero and scale commercial outcomes.",
        "competencies": "Demand Generation Strategy  •  B2B SaaS Marketing  •  Account-Based Marketing (ABM)  •  Paid Search and Paid Media  •  SEO and Content Strategy  •  Budget Ownership and ROI Reporting  •  CRM and Marketing Automation (HubSpot, Salesforce)  •  Marketing Attribution  •  Team Leadership and People Management  •  Stakeholder Management  •  Data-Driven Decision Making  •  B2B Content Marketing  •  Pipeline Revenue Growth  •  Cross-Functional Leadership",
        "employment": [
            {
                "header": "MARKETING MANAGER  |  TECHFLOW LTD  |  Feb 2021 – Present",
                "context": "Series A B2B SaaS platform targeting mid-market financial services firms. Hired as first marketing employee to build the function from scratch. Full ownership of pipeline revenue, brand, budget, and a team of 2 direct reports plus freelancer network.",
                "bullets": [
                    "Generated £4.2M in attributed pipeline revenue in FY2024 — 67% YoY — recognised by the CEO as TechFlow's single biggest commercial growth driver.",
                    "Cut wasted paid search spend from £12K to £4K per month and reduced customer acquisition cost by 31% while growing pipeline volume by 67% YoY.",
                    "Built a 120-article SEO library, scaling organic traffic from 8,000 to 47,000 monthly sessions in 18 months and establishing organic as the #1 pipeline channel.",
                    "Delivered 6 integrated campaigns per year across sales, product, and design — every campaign tied directly to quarterly revenue targets.",
                    "Implemented HubSpot CRM and full marketing automation from zero, enabling attribution reporting and pipeline visibility across the entire revenue team."
                ]
            },
            {
                "header": "DIGITAL MARKETING EXECUTIVE  |  MEDIABRIDGE UK  |  Jan 2018 – Jan 2021",
                "context": "B2B digital marketing agency managing paid and organic campaigns for a portfolio of 12 technology clients. Combined monthly ad spend under management: £180K.",
                "bullets": [
                    "Delivered 4.8x average ROAS across 12 client PPC accounts — 37% above the agency's 3.5x benchmark; ranked top 3 for commercial performance in 2019 and 2020.",
                    "Won Best B2B Campaign, Northern Digital Awards 2020 — LinkedIn ABM targeting 200 accounts; 340% ROI and 18 qualified enterprise leads.",
                    "Promoted Executive to Senior Executive in 14 months — fastest progression in the company's 12-year history.",
                    "Reduced client reporting time by 30% through Looker Studio automation across £180K monthly spend under management."
                ]
            }
        ],
        "earlier_career": [
            "Marketing Assistant  |  Digital Spark Agency  |  Sep 2016 – Feb 2018  —  Grew combined client social following by 22,000 in 12 months (target: 15,000); built email nurture sequences achieving 38% open rate against a 21% industry benchmark."
        ],
        "education": [
            "BA (Hons) Marketing, 2:1  —  University of Leeds (2013–2016)",
            "HubSpot Marketing Software Certification  —  2023",
            "Google Ads Search Certification  —  2024",
            "CIM Chartered Marketer  —  In progress, expected completion 2026"
        ],
        "technical_skills": "HubSpot  •  Salesforce  •  Google Analytics 4  •  SEMrush  •  Ahrefs  •  Google Ads  •  Meta Ads  •  LinkedIn Campaign Manager  •  Marketo  •  Webflow  •  Looker Studio  •  Notion",
        "changelog": [
            {"title": "ATS title injection", "text": "Inserted target job titles directly under the candidate name. ATS systems match on exact title keywords before a human reads the document."},
            {"title": "Professional Summary restructured", "text": "Rewritten as a four-sentence narrative: identity + metric, signature strength, breadth, career objective. Previous version read as a bullet list in paragraph form."},
            {"title": "Skills section added", "text": "Did not exist in original CV. Keyword-dense skills section acts as an ATS anchor and gives the human reader an instant capability snapshot before they assess experience."},
            {"title": "TechFlow role reframed with context subheading", "text": "Without context, a first marketing hire at an unknown Series A reads as a mid-level role. The context line clarifies scope and prevents ATS/recruiter undervaluation."},
            {"title": "ROAS and agency benchmarks added", "text": "Original CV described agency work without commercial benchmarks. Added 4.8x vs 3.5x benchmark and top-3 ranking — industry-standard performance indicators at this level."},
            {"title": "Education and Technical Skills sections added", "text": "Neither appeared in original CV. At Senior Manager / Head of level in B2B SaaS, certifications and named tools are active ATS filter criteria."}
        ],
        "gap_report": [
            {"title": "Team leadership evidence thin [HIGH PRIORITY]", "text": "CV references managing a team of 2 but lacks detail on people development or hiring. Head of Marketing roles require demonstrable people leadership. Recommended action: add one bullet per role on team-building or coaching outcomes."},
            {"title": "Marketing budget size not stated [MEDIUM PRIORITY]", "text": "Total annual marketing budget owned at TechFlow is not mentioned. Budget ownership is a standard screening criterion at Senior Manager and above. Recommended action: state the annual budget figure in the TechFlow context line."},
            {"title": "LinkedIn URL missing [LOW PRIORITY]", "text": "Contact section has no LinkedIn URL. Technology companies cross-reference LinkedIn as standard during screening. Recommended action: add full LinkedIn URL to the contact line."}
        ]
    }
    output_path = "/sessions/kind-epic-bardeen/mnt/outputs/DHM_CV_Output_James_Carter.docx"
    build_cv_doc(cv_data, output_path)
