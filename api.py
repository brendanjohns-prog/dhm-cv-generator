"""
DHM CV Optimisation API
-----------------------
Accepts Claude's structured JSON output via POST /generate
Returns a formatted .docx file ready for Google Drive upload.

Deploy to Render.com — see README in outputs folder for instructions.
"""

from flask import Flask, request, send_file, jsonify
from generate_cv import build_cv_doc
import tempfile
import os

app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health():
    """Health check — Make.com can ping this to confirm the API is live."""
    return jsonify({'status': 'ok', 'service': 'DHM CV Generator'})


@app.route('/generate', methods=['POST'])
def generate():
    """
    Accepts Claude's structured CV JSON via POST body.
    Returns a formatted .docx file as a binary download.

    Make.com HTTP module config:
      Method: POST
      URL: https://your-app.onrender.com/generate
      Body type: Raw
      Content-Type: application/json
      Body: { paste Claude's full JSON output or map {{3.data.choices[].message.content}} }
    """
    try:
        cv_data = request.get_json(force=True)

        if not cv_data:
            return jsonify({'error': 'No JSON body received'}), 400

        # Validate minimum required fields
        required = ['name', 'summary', 'employment']
        missing = [f for f in required if f not in cv_data]
        if missing:
            return jsonify({'error': f'Missing required fields: {missing}'}), 400

        # Generate .docx to a temp file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            tmp_path = tmp.name

        build_cv_doc(cv_data, tmp_path)

        # Build a clean filename from candidate name
        raw_name = cv_data.get('name', 'CV_Output')
        safe_name = raw_name.replace(' ', '_').replace('/', '-')
        filename = f"DHM_CV_{safe_name}.docx"

        response = send_file(
            tmp_path,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=filename
        )

        # Clean up temp file after response is sent
        @response.call_on_close
        def cleanup():
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        return response

    except KeyError as e:
        return jsonify({'error': f'Missing field in CV data: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
