import logging
from typing import Any

import requests
from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class SourceParser:
    """Parser for documents and web sources."""

    URL_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
    }

    @staticmethod
    def parse_pdf(source: Any) -> str:
        """Extract text from a PDF file or file-like object."""
        try:
            if hasattr(source, "seek"):
                source.seek(0)
            reader = PdfReader(source)
            text = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
            return "\n".join(text).strip()
        except Exception as exc:
            logger.error("Error parsing PDF: %s", exc)
            raise

    @staticmethod
    def parse_docx(source: Any) -> str:
        """Extract text from a DOCX file or file-like object."""
        try:
            if hasattr(source, "seek"):
                source.seek(0)
            doc = Document(source)
            return "\n".join(para.text for para in doc.paragraphs if para.text).strip()
        except Exception as exc:
            logger.error("Error parsing DOCX: %s", exc)
            raise

    @staticmethod
    def parse_text_file(source: Any) -> str:
        """Extract text from a txt or markdown source."""
        try:
            if hasattr(source, "read"):
                if hasattr(source, "seek"):
                    source.seek(0)
                raw = source.read()
                if hasattr(source, "seek"):
                    source.seek(0)
                if isinstance(raw, bytes):
                    return raw.decode("utf-8", errors="ignore").strip()
                return str(raw).strip()

            with open(source, "r", encoding="utf-8") as file_handle:
                return file_handle.read().strip()
        except Exception as exc:
            logger.error("Error parsing text source: %s", exc)
            raise

    @classmethod
    def parse_url(cls, url: str) -> str:
        """Extract the main text content from a URL."""
        try:
            response = requests.get(url, headers=cls.URL_HEADERS, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for tag in soup(["script", "style", "noscript", "header", "footer", "svg"]):
                tag.decompose()

            root = soup.find(["article", "main"]) or soup.body or soup
            text = root.get_text(separator="\n")
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            return "\n".join(chunk for chunk in chunks if chunk)
        except Exception as exc:
            logger.error("Error parsing URL %s: %s", url, exc)
            raise

    def parse(self, source: Any, source_type: str = None) -> str:
        """Centralized parsing logic."""
        normalized_type = source_type.lower() if isinstance(source_type, str) else None

        if isinstance(source, str) and source.startswith(("http://", "https://")):
            return self.parse_url(source)

        if normalized_type == "pdf" or (isinstance(source, str) and source.lower().endswith(".pdf")):
            return self.parse_pdf(source)
        if normalized_type == "docx" or (isinstance(source, str) and source.lower().endswith(".docx")):
            return self.parse_docx(source)
        if normalized_type in {"txt", "md", "text"} or (
            isinstance(source, str) and source.lower().endswith((".txt", ".md"))
        ):
            return self.parse_text_file(source)

        raise ValueError(f"Unsupported source type: {source}")
