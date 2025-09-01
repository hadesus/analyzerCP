import os
import re
import io
import docx
import requests
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask_migrate import Migrate

from config import Config
from extensions import db
from models import Analysis, DrugResult
from ai_processor import AIProcessorException
import ai_processor

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    Migrate(app, db)

    with app.app_context():
        try:
            os.makedirs(app.instance_path)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        except OSError:
            pass

    # --- Helper Functions ---
    def allowed_file(file):
        return file.filename and '.' in file.filename and \
               file.filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS'] and \
               file.mimetype == app.config['ALLOWED_MIMETYPE']

    def get_full_text_from_docx(filepath):
        """Extracts all paragraphs from a .docx file into a single string."""
        try:
            document = docx.Document(filepath)
            return "\n".join([para.text for para in document.paragraphs])
        except Exception as e:
            print(f"Error reading docx file: {e}")
            return None

    def query_pubmed(drug_name, disease):
        if not drug_name or not disease: return []
        term = f'({drug_name}[Title/Abstract]) AND ({disease}[Title/Abstract]) AND (randomized controlled trial[Publication Type] OR meta-analysis[Publication Type] OR systematic review[Publication Type])'
        params = {'db': 'pubmed', 'term': term, 'retmode': 'json', 'retmax': 3, 'tool': app.config['PUBMED_API_TOOL'], 'email': app.config['PUBMED_API_EMAIL'], 'api_key': app.config['PUBMED_API_KEY']}
        try:
            response = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params=params)
            response.raise_for_status()
            pmids = response.json().get('esearchresult', {}).get('idlist', [])
            return [f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" for pmid in pmids]
        except requests.RequestException as e:
            print(f"PubMed API request failed: {e}")
            return []

    # --- New AI-Powered Analysis Pipeline ---
    def run_full_analysis(filepath, analysis_record):
        # Step 1: Extract full text from document
        full_text = get_full_text_from_docx(filepath)
        if not full_text:
            raise ValueError("Не удалось извлечь текст из документа.")

        # Step 2: First AI Call to get context and drug list
        initial_analysis = ai_processor.analyze_document_context(full_text)
        if not initial_analysis or 'disease_context' not in initial_analysis or 'drug_list' not in initial_analysis:
            raise ValueError("Первичный анализ документа с помощью ИИ не удался или вернул неверный формат.")

        disease_context = initial_analysis['disease_context']
        raw_drug_list = initial_analysis['drug_list']

        # Step 3: Loop through drugs for detailed analysis
        for raw_drug in raw_drug_list:
            inn_protocol = raw_drug.get('inn_protocol')
            usage_protocol = raw_drug.get('usage_protocol')
            loe_protocol = raw_drug.get('loe_protocol')

            if not inn_protocol:
                continue

            # Second AI call for details
            details = ai_processor.get_drug_details(inn_protocol, usage_protocol, disease_context)
            if not details:
                details = {} # Ensure details is a dict to avoid errors on .get()

            # Query PubMed with AI-provided English name
            pubmed_links = query_pubmed(details.get('inn_english'), disease_context)

            # Create and save the final DrugResult object
            drug_result = DrugResult(
                analysis_id=analysis_record.id,
                inn_protocol=inn_protocol,
                usage_protocol=usage_protocol,
                loe_protocol=loe_protocol,
                inn_english=details.get('inn_english', 'Translation Error'),
                brief_description=details.get('brief_description', 'AI analysis failed.'),
                system_loe=details.get('system_loe', 'Unknown'),
                pubmed_links="\n".join(pubmed_links)
                # Old fields are no longer populated by this pipeline
            )
            db.session.add(drug_result)

        db.session.commit()
        return analysis_record.id

    # --- Flask Routes ---
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/upload', methods=['POST'])
    def upload_file():
        if 'file' not in request.files:
            flash('Файл не был отправлен.', 'error')
            return redirect(url_for('index'))
        file = request.files['file']
        if not file or not file.filename:
            flash('Файл не выбран.', 'error')
            return redirect(url_for('index'))
        if allowed_file(file):
            try:
                filename = secure_filename(file.filename)
                new_analysis = Analysis(filename=filename)
                db.session.add(new_analysis)
                db.session.commit()
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{new_analysis.id}_{filename}")
                file.save(filepath)

                analysis_id = run_full_analysis(filepath, new_analysis)

                flash('Анализ успешно завершен!', 'success')
                return redirect(url_for('analysis_detail', analysis_id=analysis_id))
            except (ValueError, AIProcessorException) as e:
                db.session.rollback()
                # Log the full error for debugging if needed
                print(f"Caught an analysis error: {e}")
                flash(f'Ошибка анализа: {e}', 'error')
            except Exception as e:
                db.session.rollback()
                # Catch any other unexpected errors
                print(f"An unexpected error occurred: {e}")
                flash('Произошла непредвиденная ошибка.', 'error')
        else:
            flash('Недопустимый тип или размер файла.', 'error')
        return redirect(url_for('index'))

    @app.route('/history')
    def history():
        page = request.args.get('page', 1, type=int)
        analyses = Analysis.query.order_by(Analysis.upload_timestamp.desc()).paginate(page=page, per_page=10)
        return render_template('history.html', analyses=analyses)

    @app.route('/analysis/<int:analysis_id>')
    def analysis_detail(analysis_id):
        analysis = Analysis.query.get_or_404(analysis_id)
        return render_template('analysis_detail.html', analysis=analysis)

    @app.route('/export/<int:analysis_id>')
    def export_results(analysis_id):
        analysis = Analysis.query.get_or_404(analysis_id)
        document = docx.Document()
        document.add_heading(f'Результаты Анализа: {analysis.filename}', 0)
        headers = ['Название (из протокола)', 'МНН (ENG)', 'Краткое описание', 'Ссылки PubMed', 'УД (из протокола)', 'Системный УД']
        table = document.add_table(rows=1, cols=len(headers))
        table.style = 'Table Grid'
        for i, header in enumerate(headers):
            table.cell(0, i).text = header
        for drug in analysis.drug_results:
            row_cells = table.add_row().cells
            row_cells[0].text = drug.inn_protocol or ''
            row_cells[1].text = drug.inn_english or ''
            row_cells[2].text = drug.brief_description or ''
            row_cells[3].text = drug.pubmed_links if drug.pubmed_links else "Нет"
            row_cells[4].text = drug.loe_protocol or ''
            row_cells[5].text = drug.system_loe or ''
        file_stream = io.BytesIO()
        document.save(file_stream)
        file_stream.seek(0)
        return send_file(file_stream, as_attachment=True, download_name=f'report_{analysis.id}.docx', mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

    return app

app = create_app()
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
