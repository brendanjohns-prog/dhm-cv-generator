"""
DHM CV Optimisation API
-----------------------
Accepts Claude's CV output via POST /generate — handles both:
  1. Structured JSON format: {name, tagline, employment, ...}
  2. Text draft format:      {cv_draft, strategic_changelog, gap_report}
Returns a formatted .docx file.
"""

import logging
import traceback as tb
import re
from flask import Flask, request, send_file, jsonify
from generate_cv import build_cv_doc
import tempfile
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'DHM CV Generator'})


def parse_cv_draft(cv_data):
    """
    Convert {cv_draft, strategic_changelog, gap_report} text format
    into the structured dict that build_cv_doc() expects.
    """
    raw = cv_data.get('cv_draft', '')
    # Normalise escaped newlines that Claude sometimes outputs
    raw = raw.replace('\\n', '\n')
    lines = [l for l in raw.split('\n')]
    non_empty = [l.strip() for l in lines if l.strip()]

    structured = {
        'name': non_empty[0] if len(non_empty) > 0 else 'NAME UNKNOWN',
        'tagline': non_empty[1] if len(non_empty) > 1 else '',
        'contact': non_empty[2] if len(non_empty) > 2 else '',
        'summary': '',
        'competencies': '',
        'tech_role': False,
        'technical_skills': None,
        'employment': [],
        'earlier_career': [],
        'education': [],
        'notes': '',
        'changelog': [],
        'gap_report': [],
    }

    # Section markers — order matters: more specific patterns must come before broader ones
    # (technical_skills must precede competencies to avoid TECHNICAL SKILLS matching SKILLS)
    SECTION_PATTERNS = {
        'summary':          re.compile(r'EXECUTIVE SUMMARY|PROFESSIONAL SUMMARY|CAREER SUMMARY|SUMMARY', re.I),
        'technical_skills': re.compile(r'TECHNOLOGY STACK|TECHNICAL SKILLS|TECHNOLOGY SKILLS|TOOLS AND TECHNOLOGY|TECH STACK', re.I),
        'competencies':     re.compile(r'CORE COMPETENCIES|KEY COMPETENCIES|COMPETENCIES|KEY SKILLS|SKILLS PROFILE|SKILLS', re.I),
        'employment':       re.compile(r'PROFESSIONAL EXPERIENCE|EMPLOYMENT HISTORY|WORK EXPERIENCE|EMPLOYMENT|EXPERIENCE', re.I),
        'earlier_career':   re.compile(r'EARLIER CAREER|EARLY CAREER|PREVIOUS ROLES|ADDITIONAL EXPERIENCE', re.I),
        'education':        re.compile(r'EDUCATION|QUALIFICATIONS|ACADEMIC|CERTIFICATIONS', re.I),
        'notes':            re.compile(r'^NOTES$|ADDITIONAL INFORMATION|ADDITIONAL NOTES', re.I),
    }

    current_section = None
    section_lines = []

    def flush_section():
        if not current_section or not section_lines:
            return
        content = '\n'.join(section_lines).strip()

        if current_section == 'summary':
            structured['summary'] = content

        elif current_section == 'competencies':
            structured['competencies'] = content

        elif current_section == 'technical_skills':
            structured['technical_skills'] = content

        elif current_section == 'notes':
            structured['notes'] = content  # stored but not rendered in CV

        elif current_section == 'education':
            for line in section_lines:
                line = line.strip()
                if line:
                    structured['education'].append(line)

        elif current_section in ('employment', 'earlier_career'):
            # Parse roles: header line + context + bullet points
            roles = []
            current_role = None
            for line in section_lines:
                line = line.strip()
                if not line:
                    continue
                is_bullet = line.startswith('•') or line.startswith('-') or line.startswith('*')
                # Role header: typically has | separators and a 4-digit year
                is_header = bool(re.search(r'\d{4}', line)) and '|' in line
                if is_header:
                    if current_role:
                        roles.append(current_role)
                    current_role = {'header': line, 'context': '', 'bullets': []}
                elif current_role is not None:
                    if is_bullet:
                        bullet_text = line.lstrip('•-* ').strip()
                        if bullet_text:
                            current_role['bullets'].append(bullet_text)
                    elif not current_role['context']:
                        current_role['context'] = line
                    else:
                        current_role['context'] += ' ' + line
                else:
                    # No role started yet — treat as raw earlier-career item
                    roles.append({'title': line, 'text': ''})
            if current_role:
                roles.append(current_role)

            if current_section == 'employment':
                structured['employment'] = roles
            else:
                # Earlier career: generate_cv.py expects plain strings, not dicts
                ec_items = []
                for r in roles:
                    title = r.get('header', r.get('title', ''))
                    # Strip leading bullet/dash characters
                    title = title.lstrip('-•* ').strip()
                    context = r.get('context', r.get('text', ''))
                    bullets = r.get('bullets', [])
                    combined = title
                    if context:
                        combined += ' — ' + context
                    if bullets:
                        combined += (' — ' if not context else '; ') + '; '.join(bullets)
                    if combined:
                        ec_items.append(combined)
                structured['earlier_career'] = ec_items

    for line in lines[3:]:  # Skip name/tagline/contact
        stripped = line.strip()
        matched = None
        for sec, pattern in SECTION_PATTERNS.items():
            if pattern.fullmatch(stripped) or (stripped.isupper() and len(stripped) > 3 and pattern.search(stripped)):
                matched = sec
                break

        if matched:
            flush_section()
            current_section = matched
            section_lines = []
        elif current_section:
            section_lines.append(line)

    flush_section()

    # --- Parse changelog and gap_report ---
    def parse_text_items(text):
        """Convert text blob to [{title, text}] list."""
        if not text:
            return []
        text = text.replace('\\n', '\n')
        items = []
        # Try to split on numbered list or dashes
        parts = re.split(r'\n(?=\d+[\.\)]\s|\-\s|\•\s)', text)
        for part in parts:
            part = part.strip().lstrip('0123456789.)- •')
            if not part:
                continue
            # First line = title, rest = body
            sub = part.split('\n', 1)
            title = sub[0].strip()
            body = sub[1].strip() if len(sub) > 1 else ''
            items.append({'title': title, 'text': body})
        if not items and text.strip():
            items.append({'title': 'Notes', 'text': text.strip()})
        return items

    structured['changelog'] = parse_text_items(cv_data.get('strategic_changelog', ''))
    structured['gap_report'] = parse_text_items(cv_data.get('gap_report', ''))

    return structured


@app.route('/generate', methods=['POST'])
def generate():
    try:
        raw_body = request.get_data(as_text=True)
        logger.info("=== RAW REQUEST BODY (first 500 chars) ===")
        logger.info(repr(raw_body[:500]))
        logger.info("=== CONTENT-TYPE: %s ===", request.content_type)

        cv_data = request.get_json(force=True, silent=True)

        if not cv_data:
            logger.error("JSON PARSE FAILED. Raw body repr: %r", raw_body[:200])
            return jsonify({'error': 'No JSON body received', 'raw_preview': raw_body[:200]}), 400

        if not isinstance(cv_data, dict):
            return jsonify({'error': f'Expected JSON object, got {type(cv_data).__name__}'}), 400

        logger.info("cv_data keys: %s", list(cv_data.keys()))

        # Detect format and normalise to structured dict
        if 'cv_draft' in cv_data:
            logger.info("Detected cv_draft format — converting to structured")
            cv_data = parse_cv_draft(cv_data)
            logger.info("After parse, structured keys: %s", list(cv_data.keys()))

        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            output_path = tmp.name

        build_cv_doc(cv_data, output_path)
        logger.info("Saved: %s", output_path)

        return send_file(
            output_path,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name='DHM_CV_Output.docx'
        )

    except KeyError as e:
        logger.error("KeyError: %s\n%s", e, tb.format_exc())
        return jsonify({'error': f'Missing field: {e}', 'traceback': tb.format_exc()}), 400
    except Exception as e:
        logger.error("Exception: %s\n%s", e, tb.format_exc())
        return jsonify({'error': str(e), 'traceback': tb.format_exc()}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
