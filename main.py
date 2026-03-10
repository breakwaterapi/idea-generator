import click
import logging
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv

from parser import SourceParser
from ai_client import MistralClient

# Setup Rich console
console = Console()

# Setup Logging
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console)]
)
logger = logging.getLogger("idea_generator")

load_dotenv()

def save_to_markdown(ideas, output_file="projects.md"):
    """Format the ideas as professional Markdown and save to file."""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Generated Project Ideas\n\n")
        f.write("This document contains potential project ideas extracted and generated using AI.\n\n")

        for idea in ideas:
            f.write(f"## {idea.get('project-title', 'Untitled Project')}\n")
            f.write(f"**Tech Stack:** {idea.get('tech-stack', 'Not specified')}\n\n")
            f.write(f"**Description:**  \n{idea.get('description', 'No description provided.')}\n\n")
            f.write(f"**Target Users:** {idea.get('target-users', 'Not specified')}\n\n")
            f.write(f"**First Milestone:** {idea.get('first-milestone', 'Define scope and build a prototype.')}\n\n")
            
            references = idea.get('references', [])
            if references:
                f.write("**Getting Started References:**\n")
                for ref in references:
                    title = ref.get('title', 'Reference')
                    url = ref.get('url', '#')
                    f.write(f"- [{title}]({url})\n")
                f.write("\n")

            f.write("---\n\n")

    console.print(f"\n[bold green]Success![/bold green] Extracted {len(ideas)} ideas into [cyan]{output_file}[/cyan]")

@click.command()
@click.argument('source', type=str)
@click.option('--output', '-o', default='projects.md', help='Output markdown file path')
@click.option('--api-key', help='Mistral API Key (overrides env var)')
@click.option('--ideas', '-n', default=5, show_default=True, help='Number of project ideas to generate')
@click.option('--focus', default=None, help='Optional product focus area, e.g. "Developer tools" or "B2B SaaS"')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def generate(source, output, api_key, ideas, focus, verbose):
    """
    Generate professional project ideas from a DOCUMENT or URL.
    
    SOURCE can be a path to a PDF, DOCX, TXT file, or a URL.
    """
    if verbose:
        logger.setLevel(logging.DEBUG)

    try:
        parser = SourceParser()
        client = MistralClient(api_key=api_key)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            
            # Step 1: Parsing
            task1 = progress.add_task(description=f"Parsing source: {source}...", total=None)
            context = parser.parse(source)
            progress.update(task1, completed=True, description="Parsing complete.")

            if not context:
                console.print("[bold red]Error:[/bold red] No text extracted from source.")
                return

            # Step 2: Generation
            task2 = progress.add_task(description="Consulting AI for project ideas...", total=None)
            generated_ideas = client.generate_project_ideas(context, idea_count=ideas, focus_area=focus)
            progress.update(task2, completed=True, description="Generation complete.")

            # Step 3: Saving
            save_to_markdown(generated_ideas, output)

    except Exception as e:
        console.print(f"\n[bold red]Fatal Error:[/bold red] {str(e)}")
        if verbose:
            console.print_exception()

if __name__ == "__main__":
    generate()
