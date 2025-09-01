import fitz  # PyMuPDF
import re

def clean_drug_name(line):
    """
    Cleans a line to extract a potential drug name.
    """
    # Remove leading symbols like ''
    line = re.sub(r'^\s*\s*', '', line)
    # Handle therapeutic alternatives starting with '-'
    line = re.sub(r'^\s*-\s*', '', line)
    # Remove content in parentheses
    line = re.sub(r'\(.*\)', '', line)
    # Remove trailing notes and symbols
    line = re.sub(r'\s*\[c\]\s*$', '', line)
    line = re.sub(r'\s+a\s*$', '', line)
    line = re.sub(r'\s*\*\s*$', '', line) # Remove trailing asterisk
    return line.strip()

def is_dosage_form(line):
    """
    Checks if a line describes a dosage form.
    """
    dosage_starters = [
        "tablet", "injection", "oral liquid", "solid oral", "capsule",
        "powder for", "rectal", "transdermal", "solution", "concentrate",
        "inhalation", "pessary", "gel", "enema", "suppository", "lozenge"
    ]
    return any(line.lower().strip().startswith(starter) for starter in dosage_starters)

def is_header_or_footer(line):
    """
    Checks if a line is likely a header, footer, or section title.
    """
    line_lower = line.lower()
    if "who model list" in line_lower or "page" in line_lower:
        return True
    if re.match(r'^\d+(\.\d+)*\s', line): # Matches "1.", "2.3", "6.1.1" etc.
        return True
    if line_lower.strip() in ["complementary list", "therapeutic alternatives:"]:
        return True
    return False

def is_valid_drug_name(name):
    """
    Validates if the cleaned string is a plausible drug name.
    """
    if len(name) < 3: # Too short
        return False
    if not re.match(r'^[a-z\s\-+]+$', name): # Must contain only letters, spaces, hyphens, plus
        return False
    return True


def parse_who_eml_pdf(pdf_path, output_path):
    """
    Parses the WHO EML PDF to extract a clean list of drug names.
    """
    drug_names = set()
    try:
        document = fitz.open(pdf_path)

        in_alternatives_section = False
        for page_num in range(document.page_count):
            page = document.load_page(page_num)
            text = page.get_text("text")
            lines = text.split('\n')

            for i, line in enumerate(lines):
                line_lower_stripped = line.strip().lower()
                if not line_lower_stripped or is_header_or_footer(line) or is_dosage_form(line):
                    if "therapeutic alternatives" in line_lower_stripped:
                        in_alternatives_section = True
                    else:
                        if not line_lower_stripped.startswith("-"):
                            in_alternatives_section = False
                    continue

                cleaned_name = clean_drug_name(line_lower_stripped)

                if not is_valid_drug_name(cleaned_name):
                    continue

                # Handle drugs listed under "Therapeutic alternatives"
                if in_alternatives_section and line.strip().startswith("-"):
                    drug_names.add(cleaned_name)
                    continue

                # Main drug name detection logic
                if i + 1 < len(lines) and is_dosage_form(lines[i+1]):
                    drug_names.add(cleaned_name)

        with open(output_path, 'w', encoding='utf-8') as f:
            for name in sorted(list(drug_names)):
                f.write(name + '\n')

        print(f"--- Successfully extracted {len(drug_names)} unique drug names to '{output_path}' ---")

    except Exception as e:
        print(f"An error occurred during PDF parsing: {e}")

if __name__ == "__main__":
    parse_who_eml_pdf("who_eml_2023.pdf", "who_eml_drug_list.txt")
