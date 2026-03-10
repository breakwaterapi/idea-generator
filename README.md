# AI Idea Generator(VIBE CODED)

Turn technical content (PDFs, DOCX, TXT, MD, or URLs) into polished, professional product concepts using Mistral AI.

This project extracts text from a given source and generates structured project ideas including technical stack suggestions, descriptions, target users, and the first major milestone.

## Features

- **Document Analysis**: Upload or parse PDF, DOCX, Markdown, or raw Text files.
- **URL Parsing**: Extract meaningful content directly from technical articles or documentation URLs.
- **Mistral AI Powered**: Generates high-quality, actionable product concepts.
- **Dual Interfaces**:
  - **CLI**: Quickly process files via command line.
  - **Web UI**: Modern web interface built with Flask for a polished user experience.

## Installation

1. Clone the repository and navigate into it.
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your Mistral API key:
   - Create a `.env` file in the root directory.
   - Add your Mistral API key:
     ```env
     MISTRAL_API_KEY=your_api_key_here
     ```

## Usage

### Command Line Interface (CLI)

Use `main.py` to generate ideas from the terminal.

```bash
python main.py sample_context.txt --output projects.md --ideas 5
```

Options:
- `--output` / `-o`: Output markdown file path (default: `projects.md`)
- `--ideas` / `-n`: Number of project ideas to generate (default: 5)
- `--focus`: Optional product focus area (e.g., "Developer tools")
- `--api-key`: Mistral API Key (overrides `.env` variable)
- `--verbose` / `-v`: Enable verbose logging

### Web Interface (Flask)

Start the local Flask development server for local testing:

```bash
python app.py
```

Then open `http://127.0.0.1:5000` in your web browser. The web UI allows you to upload files or paste URLs, select focus areas, and view/download the output.

### Docker Deployment (Production)

To deploy the Idea Generator in a production-ready container using Gunicorn:

1. Ensure your `.env` file is present with your `MISTRAL_API_KEY`.
2. Build the Docker image:
   ```bash
   docker build -t idea-generator .
   ```
3. Run the container:
   ```bash
   docker run -d -p 5000:5000 --env-file .env --name idea-generator-app idea-generator
   ```

The application will now be running at `http://localhost:5000`.

## Tech Stack

- **Python 3**
- **MistralAI API** (Replaced Gemini API in newer versions)
- **Flask** (Web Framework)
- **BeautifulSoup4** (Web scraping)
- **PyPDF / python-docx** (Document parsing)
- **Rich / Click** (CLI UI)
