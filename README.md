# Protocol-Analyzer

Protocol-Analyzer is a web application designed to automate the process of extracting, analyzing, and verifying lists of medications from clinical protocol documents. It checks the extracted drugs against international formularies and regulatory approvals to generate a comprehensive analysis report.

## Features

-   **Web-Based Interface**: Modern and clean UI for uploading `.docx` files.
-   **DOCX Parsing**: Automatically finds and extracts drug information from tables within Word documents.
-   **NLP Pipeline**:
    -   Parses complex "usage" strings to extract structured data (dosage, units, route, frequency).
    -   Standardizes medical terms to a common format.
    -   Translates Russian drug names (INNs) to English for international database queries.
-   **Multi-Source Verification**:
    -   Checks against a local formulary built from the WHO Essential Medicines List.
    -   Queries the FDA and EMA websites for regulatory approval status.
    -   Searches PubMed for relevant clinical trials and meta-analyses.
-   **System-Generated Level of Evidence**: Assigns a Level of Evidence (LoE) based on the quality of findings on PubMed.
-   **Comprehensive Reporting**: Displays the full analysis in a clear table on a results web page.
-   **Word Export**: Allows the user to download the final report as a `.docx` file.

## Setup

Follow these steps to set up and run the project locally.

### 1. Prerequisites

-   Python 3.7+

### 2. Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # On Windows, use: venv\Scripts\activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### 3. One-Time Data Preparation

The application uses a local copy of the WHO Essential Medicines List (EML) for verification. You need to generate this data file by running the included parser script. This script will download the official PDF from the WHO website, parse it, and create a local drug list.

**Run the parser:**
```bash
python3 formulary_parser.py
```
This will create a `who_eml_drug_list.txt` file in the root directory. This step only needs to be done once.

## Running the Application

Once the setup is complete, you can start the Flask web server:

```bash
python3 app.py
```

The application will be available at `http://127.0.0.1:8080`.

## Usage

1.  Open your web browser and navigate to `http://127.0.0.1:8080`.
2.  Use the file upload form to select a clinical protocol in `.docx` format.
3.  Click the "Анализировать" (Analyze) button.
4.  You will be redirected to the results page, which will display a detailed table with the analysis for each drug found in the document.
5.  On the results page, you can click the "Экспорт в Word (.docx)" (Export to Word) button to download the report as a Word document.
