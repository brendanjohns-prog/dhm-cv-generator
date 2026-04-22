import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['PDFSHIFT_API_KEY'] = 'sk_13d15b19a7335a343a34a326c1c2ccfa65cdfa3a'

from api import parse_cv_draft, clean_cv_data, apply_voice_fix, render_report_pdf

# Simulate Julian's actual Claude output length (~70-80 word gap bodies)
claude_output = {
    "cv_draft": "JULIAN CARTER\nSenior Marketing Manager | Head of Marketing | Demand Generation Lead\nemail@test.com",
    "strategic_changelog": (
        "1. **ATS title injection and positioning fix** - Target job titles now sit in the header. ATS systems match on exact title strings before a human reads a word. Candidates without those strings are filtered out at the first screen.\n\n"
        "2. **Summary restructured around strongest metric** - The Executive Summary opens with your four strongest proof points. Hiring managers spend roughly six seconds deciding whether to read on. The numbers must land before the eye moves down.\n\n"
        "3. **Core Competencies section added before experience** - This block did not exist before. A keyword-dense cluster gives ATS systems a clean match signal and human readers an instant capability snapshot.\n\n"
        "4. **Title mismatch addressed in the TechFlow context line** - Your TechFlow title is Marketing Manager but scope is Head of Marketing-level. The context subheading reframes seniority without inflating the title.\n\n"
        "5. **Achievement bullets restructured to outcome-first format** - Every bullet in the rewrite opens with the result. Scanners find the number in the first five words. Context follows rather than leading the sentence.\n\n"
        "6. **Cross-functional leadership reframed** - Your direct team is two, short of the 5+ requirement. The rewrite references cross-functional team leadership of up to 8 people, demonstrating coordination scope."
    ),
    "gap_report": (
        "1. **Formal people management scope is thin [HIGH PRIORITY]** - Senior marketing roles at Head of level consistently require direct line management of 5 or more people, and your current direct report count is 2. This is the single most common filter applied at the screening stage for roles you are targeting. Recommended action: quantify your cross-functional project team leadership of up to 8 people explicitly in every application and interview to close this gap narratively.\n\n"
        "2. **Job title mismatch with target seniority [HIGH PRIORITY]** - Your title is Marketing Manager but your scope, budget ownership, and revenue impact match a Head of Marketing profile. Title mismatch is the primary reason your CV is not clearing initial screening filters on job boards. Recommended action: negotiate a title upgrade to Senior Marketing Manager or Head of Marketing at TechFlow before your next application round if at all possible.\n\n"
        "3. **No marketing budget figure stated on the CV [HIGH PRIORITY]** - Budget ownership is a listed requirement in the majority of Senior Manager and Head of Marketing adverts, and your CV does not name a total annual figure. Without a number, screeners cannot confirm you meet the budget threshold they are filtering for. Recommended action: establish your total controlled marketing budget figure at TechFlow and add it to the TechFlow role context line immediately.\n\n"
        "4. **No named ABM platform or tool [MEDIUM PRIORITY]** - You won an ABM award and mention ABM as a competency, but no dedicated ABM platform such as Demandbase, 6sense, or Terminus appears in your tools list. Many senior B2B marketing roles in technology filter for these by exact name. Recommended action: if you have used any ABM technology, even briefly, add it to your Technical Skills section.\n\n"
        "5. **No Marketo use evidenced in role context [MEDIUM PRIORITY]** - Marketo appears in your tools list but is not evidenced in any role bullet. At Head of Marketing level in technology, hiring managers expect marketing automation platforms named within pipeline or revenue outcomes. Recommended action: add a brief reference to Marketo in the TechFlow or MediaBridge context where accurate.\n\n"
        "6. **CIM not yet completed [LOW PRIORITY]** - The CIM Chartered Marketer is in progress with a 2026 completion date. Some senior job adverts list CIM Level 6 or Chartered status as a preference. This is unlikely to filter you out but could be a tiebreaker against candidates who already hold the qualification. Recommended action: continue on the current timeline and reference it as in progress on the CV."
    )
}

cv_data = parse_cv_draft(claude_output)
cv_data['tagline'] = 'Senior Marketing Manager | Head of Marketing | Demand Generation Lead'
cv_data['name'] = 'Julian Carter'
cv_data = clean_cv_data(cv_data)
cv_data = apply_voice_fix(cv_data)

pdf = render_report_pdf(cv_data)
with open('/tmp/julian_v10.pdf', 'wb') as f:
    f.write(pdf)
print(f"Wrote {len(pdf)} bytes")
