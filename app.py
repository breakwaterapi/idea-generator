import io
import logging
import os
from datetime import datetime
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, flash, render_template, request, send_file

from ai_client import MistralClient
from parser import SourceParser

load_dotenv()

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "idea-generator-dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}
FOCUS_OPTIONS = [
    "General",
    "Developer tools",
    "AI automation",
    "Data products",
    "B2B SaaS",
    "Consumer apps",
    "Internal operations",
]


def is_valid_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def render_stack_badges(stack: str) -> list[str]:
    badges = []
    for part in stack.replace("/", ",").split(","):
        cleaned = part.strip()
        if cleaned:
            badges.append(cleaned)
    return badges or ["Not specified"]


def parse_idea_count(raw_value: str) -> int:
    try:
        return max(3, min(8, int(raw_value)))
    except (TypeError, ValueError):
        return 5


def build_markdown_export(ideas: list[dict], source_label: str, generated_at: datetime | None, focus_area: str) -> str:
    generated_label = generated_at.strftime("%Y-%m-%d %H:%M") if generated_at else "Unknown"
    markdown = [
        "# Generated Project Ideas",
        "",
        f"- **Generated:** {generated_label}",
        f"- **Source:** {source_label or 'Unknown'}",
        f"- **Focus Area:** {focus_area}",
        "",
    ]

    for idea in ideas:
        markdown.extend(
            [
                f"## {idea.get('project-title', 'Untitled Project')}",
                f"**Tech Stack:** {idea.get('tech-stack', 'Not specified')}",
                "",
                "**Description:**  ",
                idea.get("description", "No description provided."),
                "",
                f"**Target Users:** {idea.get('target-users', 'Not specified')}",
                "",
                f"**First Milestone:** {idea.get('first-milestone', 'Define scope and build a prototype.')}",
                "",
            ]
        )

        references = idea.get('references', [])
        if references:
            markdown.append("**Getting Started References:**")
            for ref in references:
                title = ref.get('title', 'Reference')
                url = ref.get('url', '#')
                markdown.append(f"- [{title}]({url})")
            markdown.append("")

        markdown.extend(
            [
                "---",
                "",
            ]
        )

    return "\n".join(markdown)


@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    context_preview = ""
    source_label = ""
    generated_at = None
    markdown_export = ""

    form_data = {
        "api_key": os.getenv("MISTRAL_API_KEY", ""),
        "idea_count": 5,
        "focus_area": "General",
        "source_mode": "document",
        "url_input": "",
    }

    if request.method == "POST":
        form_data["api_key"] = request.form.get("api_key", "").strip()
        form_data["idea_count"] = parse_idea_count(request.form.get("idea_count", 5))
        form_data["focus_area"] = request.form.get("focus_area", "General")
        form_data["source_mode"] = request.form.get("source_mode", "document")
        form_data["url_input"] = request.form.get("url_input", "").strip()

        if not form_data["api_key"]:
            flash("Add your Mistral API key before generating ideas.", "error")
            return render_template(
                "index.html",
                focus_options=FOCUS_OPTIONS,
                form_data=form_data,
                results=results,
                context_preview=context_preview,
                source_label=source_label,
                generated_at=generated_at,
                markdown_export=markdown_export,
                render_stack_badges=render_stack_badges,
            )

        try:
            parser = SourceParser()
            client = MistralClient(api_key=form_data["api_key"])

            if form_data["source_mode"] == "url":
                if not form_data["url_input"] or not is_valid_url(form_data["url_input"]):
                    flash("Enter a valid URL before starting the analysis.", "error")
                    raise ValueError("Invalid URL")

                source = form_data["url_input"]
                source_type = None
                source_label = form_data["url_input"]
            else:
                uploaded_file = request.files.get("document")
                if not uploaded_file or not uploaded_file.filename:
                    flash("Upload a PDF, DOCX, TXT, or Markdown file.", "error")
                    raise ValueError("Missing file")

                extension = uploaded_file.filename.rsplit(".", 1)[-1].lower() if "." in uploaded_file.filename else ""
                if extension not in ALLOWED_EXTENSIONS:
                    flash("Unsupported file type. Use PDF, DOCX, TXT, or MD.", "error")
                    raise ValueError("Unsupported file type")

                source = uploaded_file.stream
                source_type = extension
                source_label = uploaded_file.filename

            context = parser.parse(source, source_type=source_type)
            if not context or len(context.strip()) < 120:
                flash("The extracted content is too short. Try a richer source with more technical detail.", "error")
                raise ValueError("Insufficient content")

            results = client.generate_project_ideas(
                context,
                idea_count=form_data["idea_count"],
                focus_area=None if form_data["focus_area"] == "General" else form_data["focus_area"],
            )
            generated_at = datetime.now()
            context_preview = context[:3000] + ("..." if len(context) > 3000 else "")
            markdown_export = build_markdown_export(results, source_label, generated_at, form_data["focus_area"])
            flash(f"Generated {len(results)} idea candidates.", "success")
        except ValueError:
            if not results and not markdown_export:
                context_preview = ""
                source_label = source_label or ""
        except Exception as exc:
            logger.exception("Failed to generate project ideas")
            flash(f"Generation failed: {exc}", "error")

    return render_template(
        "index.html",
        focus_options=FOCUS_OPTIONS,
        form_data=form_data,
        results=results,
        context_preview=context_preview,
        source_label=source_label,
        generated_at=generated_at,
        markdown_export=markdown_export,
        render_stack_badges=render_stack_badges,
    )


@app.post("/download")
def download_markdown():
    content = request.form.get("markdown_export", "").strip()
    if not content:
        flash("Nothing to download yet. Generate ideas first.", "error")
        return render_template(
            "index.html",
            focus_options=FOCUS_OPTIONS,
            form_data={
                "api_key": os.getenv("MISTRAL_API_KEY", ""),
                "idea_count": 5,
                "focus_area": "General",
                "source_mode": "document",
                "url_input": "",
            },
            results=[],
            context_preview="",
            source_label="",
            generated_at=None,
            markdown_export="",
            render_stack_badges=render_stack_badges,
        )

    file_buffer = io.BytesIO(content.encode("utf-8"))
    file_buffer.seek(0)
    return send_file(
        file_buffer,
        as_attachment=True,
        download_name="project_ideas.md",
        mimetype="text/markdown",
    )


if __name__ == "__main__":
    app.run(debug=True)
