# Protocol-Analyzer

Protocol-Analyzer is a web application that uses Artificial Intelligence to automate the process of extracting and analyzing lists of medications from clinical protocol documents.

## Features

-   **Web Interface**: A modern and clean user interface for uploading `.docx` files.
-   **AI-Powered Analysis**:
    -   Determines the main disease or clinical context of the protocol.
    -   Extracts a complete list of medications.
    -   Retrieves the English INN (International Nonproprietary Name) for each drug.
    -   Generates a brief description of the drug's role in treatment.
    -   Assesses the level of evidence based on the AI's knowledge base.
-   **PubMed Integration**: Automatically searches for relevant clinical trials and meta-analyses for each drug.
-   **Comprehensive Reporting**: Displays the full analysis in a clear table on the results page.
-   **Word Export**: Allows downloading the final report as a `.docx` file.

## Setup and Installation

Follow these steps to set up and run the project locally.

### 1. Prerequisites

-   Python 3.7+
-   A Google Gemini API Key (see below)

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

### 3. API Key Configuration

The application requires API access to Google Gemini and PubMed.

1.  **Create a `.env` file** in the project's root directory.
2.  **Add your API keys to it:**
    ```
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    PUBMED_API_KEY="YOUR_PUBMED_API_KEY" # Optional, but recommended
    PUBMED_API_TOOL="ProtocolAnalyzer"
    PUBMED_API_EMAIL="your.email@example.com"
    ```
   - Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
   - A PubMed API key can be obtained from [your NCBI account](https://www.ncbi.nlm.nih.gov/account/).

### 4. Apply Database Migrations
On the first run or after a data model update, you need to apply the database migrations:
```bash
flask db upgrade
```

## Running the Application

Once the setup is complete, you can start the Flask web server:

```bash
python3 app.py
```

The application will be available at `http://127.0.0.1:8080`.

## Usage

1.  Open your web browser and navigate to `http://127.0.0.1:8080`.
2.  Use the file upload form to select a clinical protocol in `.docx` format.
3.  Click the "Analyze" button.
4.  You will be redirected to the results page, which displays a detailed table with the analysis for each drug found.
5.  On the results page, you can click the "Export to Word (.docx)" button to download the report.
