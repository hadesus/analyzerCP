import os
import re
import io
import docx
import translators as ts
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file

# --- Constants & Global Data ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'docx'}
PUBMED_API_KEY = 'cef64c4511a6cade69c74298b9227bff3508'
PUBMED_API_TOOL = 'Protocol-Analyzer'
PUBMED_API_EMAIL = 'ayat.asemov@gmail.com'
WHO_EML_DRUGS = set()

# --- Mappings ---
ROUTE_MAP = {
    'в/в': 'intravenous', 'внутривенно': 'intravenous', 'капельно': 'intravenous drip',
    'в/м': 'intramuscular', 'внутримышечно': 'intramuscular', 'п/к': 'subcutaneous',
    'подкожно': 'subcutaneous', 'перорально': 'oral', 'per os': 'oral'
}
UNITS_MAP = {
    'мг': 'mg', 'г': 'g', 'мл': 'ml', 'мкг': 'mcg', 'ме': 'iu', 'ед': 'iu', 'ui': 'iu', 'iu': 'iu'
}
# -----------------------------

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'a_very_secret_key_for_sessions'

def load_formulary_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            drugs = {line.strip().lower() for line in f if line.strip()}
        print(f"--- Loaded {len(drugs)} drugs from {file_path} ---")
        return drugs
    except FileNotFoundError:
        print(f"--- Formulary file not found: {file_path} ---")
        return set()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_drug_data_from_docx(filepath):
    try:
        document = docx.Document(filepath)
        extracted_drugs = []
        required_headers = {"inn": "международное непатентованное наименование лс", "usage": "способ применения", "loe": ["уд", "уровень доказательности"]}
        for table in document.tables:
            headers = [cell.text.strip().lower() for cell in table.rows[0].cells]
            if required_headers["inn"] in headers and required_headers["usage"] in headers:
                loe_header = next((h for h in required_headers["loe"] if h in headers), None)
                for i in range(1, len(table.rows)):
                    cells = table.rows[i].cells
                    inn = cells[headers.index(required_headers["inn"])].text.strip()
                    if inn:
                        extracted_drugs.append({
                            "inn_protocol": inn,
                            "usage_protocol": cells[headers.index(required_headers["usage"])].text.strip(),
                            "loe_protocol": cells[headers.index(loe_header)].text.strip() if loe_header else "Н/У"
                        })
        return extracted_drugs
    except Exception as e:
        print(f"Error parsing DOCX: {e}")
        return None

def query_pubmed(drug_name, disease):
    if not drug_name or drug_name == "Translation Error" or not disease: return []
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    search_params = {'db': 'pubmed', 'term': f'({drug_name}[Title/Abstract]) AND ({disease}[Title/Abstract]) AND (randomized controlled trial[Publication Type] OR meta-analysis[Publication Type])', 'retmode': 'json', 'retmax': 3, 'tool': PUBMED_API_TOOL, 'email': PUBMED_API_EMAIL, 'api_key': PUBMED_API_KEY}
    try:
        response = requests.get(f"{base_url}esearch.fcgi", params=search_params)
        response.raise_for_status()
        pmids = response.json().get('esearchresult', {}).get('idlist', [])
        return [f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" for pmid in pmids]
    except requests.RequestException as e:
        print(f"PubMed API request failed: {e}")
        return []

def query_regulatory_body(drug_name, body):
    if not drug_name or drug_name == "Translation Error": return "N/A"
    try:
        if body == "FDA":
            url = f"https://www.accessdata.fda.gov/scripts/cder/drugsatfda/index.cfm?fuseaction=Search.Search_Drug_Name&DrugName={drug_name}"
            selector = ("table", {"id": "results-table"})
        elif body == "EMA":
            url = f"https://www.ema.europa.eu/en/medicines/search/ema_group_types/ema_medicine?search_api_views_fulltext={drug_name}"
            selector = ("div", {"class": "view-medicines-search"})
        else: return "Unknown Body"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return "Found" if soup.find(*selector) else "Not Found"
    except Exception as e:
        print(f"{body} scraping failed for {drug_name}: {e}")
        return "Scraping Error"

def assign_system_loe(drug):
    if drug.get("pubmed_links"): drug["system_loe"] = "Класс I (A)"
    else: drug["system_loe"] = "Класс IV (D)"

def run_full_analysis(filepath):
    drug_list = extract_drug_data_from_docx(filepath)
    if drug_list is None: return None
    disease_placeholder = "cancer"
    for drug in drug_list:
        usage_str = drug.get("usage_protocol", "")
        dosage_match = re.search(r'(\d+[\.,]?\d*)\s*(мг|г|мл|мкг|ме|ед|ui|iu)', usage_str, re.IGNORECASE)
        drug["parsed_dosage"] = dosage_match.group(1).replace(',', '.') if dosage_match else "Н/У"
        drug["parsed_units"] = dosage_match.group(2).lower() if dosage_match else "Н/У"
        drug["parsed_frequency"] = re.search(r'(\d+\s*раз\w*\s*в\s*\w+)', usage_str, re.IGNORECASE).group(1) if re.search(r'(\d+\s*раз\w*\s*в\s*\w+)', usage_str, re.IGNORECASE) else "Н/У"
        route_match = re.search(r'(в/в|внутривенно|в/м|внутримышечно|п/к|подкожно|перорально|per os|капельно)', usage_str, re.IGNORECASE)
        drug["parsed_route"] = route_match.group(1).lower() if route_match else "Н/У"
        drug["normalized_route"] = ROUTE_MAP.get(drug["parsed_route"], "unknown")
        drug["normalized_units"] = UNITS_MAP.get(drug["parsed_units"], "unknown")
        try:
            drug["inn_english"] = ts.translate_text(drug.get("inn_protocol", ""), to_language='en', from_language='ru')
        except Exception as e:
            print(f"Translation error: {e}")
            drug["inn_english"] = "Translation Error"
        inn_eng = drug.get("inn_english", "").lower()
        drug["pubmed_links"] = query_pubmed(inn_eng, disease_placeholder)
        drug["fda_status"] = query_regulatory_body(inn_eng, "FDA")
        drug["ema_status"] = query_regulatory_body(inn_eng, "EMA")
        drug["who_eml_status"] = "Found" if inn_eng in WHO_EML_DRUGS else "Not Found"
        assign_system_loe(drug)
    return drug_list

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('Не удалось найти файл', 'error')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(filepath)
        processed_data = run_full_analysis(filepath)
        if processed_data is not None:
            session['results'] = processed_data
            return redirect(url_for('results'))
        else:
            flash('Ошибка при анализе файла.', 'error')
            return redirect(url_for('index'))
    else:
        flash('Разрешены только файлы с расширением .docx', 'error')
        return redirect(url_for('index'))

@app.route('/results')
def results():
    results_data = session.get('results', [])
    if not results_data:
        return redirect(url_for('index'))
    return render_template('results.html', results=results_data)

@app.route('/export')
def export_results():
    results_data = session.get('results', [])
    if not results_data:
        flash('Нет данных для экспорта.', 'error')
        return redirect(url_for('index'))

    document = docx.Document()
    document.add_heading('Результаты Анализа Протокола', 0)
    headers = ['Название (из протокола)', 'МНН (ENG)', 'Применение (из протокола)', 'Статус в источниках', 'Ссылки PubMed', 'УД (из протокола)', 'Системный УД']
    table = document.add_table(rows=1, cols=len(headers))
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    for i, header in enumerate(headers):
        hdr_cells[i].text = header

    for drug in results_data:
        row_cells = table.add_row().cells
        row_cells[0].text = drug.get('inn_protocol', '')
        row_cells[1].text = drug.get('inn_english', '')
        row_cells[2].text = drug.get('usage_protocol', '')
        status_text = f"WHO EML: {drug.get('who_eml_status', '')}\nFDA: {drug.get('fda_status', '')}\nEMA: {drug.get('ema_status', '')}"
        row_cells[3].text = status_text
        pubmed_text = '\n'.join(drug.get('pubmed_links', []))
        row_cells[4].text = pubmed_text if pubmed_text else "Нет"
        row_cells[5].text = drug.get('loe_protocol', '')
        row_cells[6].text = drug.get('system_loe', '')

    file_stream = io.BytesIO()
    document.save(file_stream)
    file_stream.seek(0)
    return send_file(file_stream, as_attachment=True, download_name='protocol_analysis_report.docx', mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

if __name__ == '__main__':
    WHO_EML_DRUGS = load_formulary_data('who_eml_drug_list.txt')
    app.run(debug=True, host='0.0.0.0', port=8080)
