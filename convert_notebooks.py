#!/usr/bin/env python3
"""
Convert Jupyter notebooks to HTML chapters for the linear regression website.
"""

import json
import re
import shutil
from pathlib import Path
from html import escape
import markdown

# Excluded notebooks
EXCLUDED_NOTEBOOKS = [
    "ridge_regression_example.ipynb",
    "10_1_Linear_regression_regularization_code.ipynb",
]

# Source and destination directories
SOURCE_DIR = Path(
    "/Users/in-divye.singh/Documents/Projects/study_materials/Machine_learning/Linear_regression"
)
DEST_DIR = Path(__file__).parent
CHAPTERS_DIR = DEST_DIR / "chapters"
ASSETS_DIR = DEST_DIR / "assets" / "images"

# Create directories
CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Initialize markdown converter
md = markdown.Markdown(extensions=["codehilite", "fenced_code", "tables", "nl2br"])


def extract_chapter_number(filename):
    """Extract chapter number from filename for sorting."""
    match = re.match(r"^(\d+)", filename)
    if match:
        return int(match.group(1))
    return 999  # Put unnumbered files at the end


def sanitize_filename(filename):
    """Convert notebook filename to HTML filename."""
    return filename.replace(".ipynb", ".html")


def get_chapter_title(notebook_path):
    """Extract title from first markdown cell."""
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Look for first markdown cell with a heading
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "markdown":
            source = "".join(cell.get("source", []))
            # Extract first heading or use filename
            lines = source.strip().split("\n")
            for line in lines:
                if line.startswith("#"):
                    # Remove markdown heading markers
                    title = re.sub(r"^#+\s*", "", line).strip()
                    if title:
                        return title

    # Fallback to filename
    return notebook_path.stem.replace("_", " ").title()


def convert_output_to_html(output):
    """Convert notebook output to HTML."""
    output_type = output.get("output_type", "")

    if output_type == "stream":
        text = "".join(output.get("text", []))
        return f'<pre class="output-text">{escape(text)}</pre>'

    elif output_type == "execute_result" or output_type == "display_data":
        data = output.get("data", {})

        # Handle text/plain
        if "text/plain" in data:
            text = "".join(data["text/plain"])
            return f'<pre class="output-text">{escape(text)}</pre>'

        # Handle HTML
        if "text/html" in data:
            html = "".join(data["text/html"])
            return f'<div class="output-html">{html}</div>'

        # Handle images
        if "image/png" in data:
            img_data = data["image/png"]
            if isinstance(img_data, str):
                return f'<img src="data:image/png;base64,{img_data}" class="output-image" alt="Output image">'

        # Handle LaTeX
        if "text/latex" in data:
            latex = "".join(data["text/latex"])
            return f'<div class="output-latex">$${latex}$$</div>'

    return ""


def markdown_to_html(markdown_text):
    """Convert markdown to HTML while preserving LaTeX."""
    # Use HTML comments as placeholders (markdown won't process them)
    import uuid

    latex_map = {}
    text = markdown_text

    # Protect align blocks first (they may contain $)
    align_pattern = r"\\begin\{align\*?\}.*?\\end\{align\*?\}"
    for match in reversed(list(re.finditer(align_pattern, text, re.DOTALL))):
        unique_id = str(uuid.uuid4()).replace("-", "")
        placeholder = f"<!--LATEX_{unique_id}-->"
        latex_map[placeholder] = match.group(0)
        start, end = match.span()
        text = text[:start] + placeholder + text[end:]

    # Protect display math ($$...$$)
    display_pattern = r"\$\$.*?\$\$"
    for match in reversed(list(re.finditer(display_pattern, text, re.DOTALL))):
        unique_id = str(uuid.uuid4()).replace("-", "")
        placeholder = f"<!--LATEX_{unique_id}-->"
        latex_map[placeholder] = match.group(0)
        start, end = match.span()
        text = text[:start] + placeholder + text[end:]

    # Protect inline math ($...$) - but not $$...$$
    # Match $...$ that's not part of $$
    inline_pattern = r"(?<!\$)\$[^$\n]+\$(?!\$)"
    for match in reversed(list(re.finditer(inline_pattern, text))):
        unique_id = str(uuid.uuid4()).replace("-", "")
        placeholder = f"<!--LATEX_{unique_id}-->"
        latex_map[placeholder] = match.group(0)
        start, end = match.span()
        text = text[:start] + placeholder + text[end:]

    # Convert markdown to HTML
    md.reset()
    html = md.convert(text)

    # Restore LaTeX blocks
    for placeholder, latex_content in latex_map.items():
        html = html.replace(placeholder, latex_content)

    return html


def process_notebook(notebook_path, chapter_index, total_chapters):
    """Convert a single notebook to HTML."""
    print(f"Processing {notebook_path.name}...")

    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    title = get_chapter_title(notebook_path)
    html_filename = sanitize_filename(notebook_path.name)

    html_content = []
    # Generate content-only HTML (just the chapter-content div)
    html_content.append('<div class="chapter-content">')
    html_content.append(f'    <h1 class="chapter-title">{escape(title)}</h1>')

    cell_counter = 0
    for cell in nb.get("cells", []):
        cell_type = cell.get("cell_type", "")
        source = "".join(cell.get("source", []))

        if not source.strip() and cell_type == "markdown":
            continue

        if cell_type == "markdown":
            # Convert markdown to HTML while preserving LaTeX
            html = markdown_to_html(source)
            html_content.append(f'    <div class="markdown-cell">{html}</div>')

        elif cell_type == "code":
            cell_id = f"code-cell-{cell_counter}"
            cell_counter += 1

            # Code cell (collapsible)
            html_content.append('    <div class="code-cell-container">')
            html_content.append(
                f'        <button class="code-toggle" onclick="toggleCodeCell(\'{cell_id}\')">'
            )
            html_content.append('            <span class="toggle-icon">▶</span>')
            html_content.append('            <span class="toggle-text">Show Code</span>')
            html_content.append("        </button>")
            html_content.append(
                f'        <div class="code-cell" id="{cell_id}" style="display: none;">'
            )
            html_content.append(
                f'            <pre><code class="language-python">{escape(source)}</code></pre>'
            )
            html_content.append("        </div>")
            html_content.append("    </div>")

            # Outputs (optional/collapsible)
            outputs = cell.get("outputs", [])
            if outputs:
                output_id = f"output-{cell_id}"
                html_content.append('    <div class="output-container">')
                html_content.append(
                    f'        <button class="output-toggle" onclick="toggleOutput(\'{output_id}\')">'
                )
                html_content.append('            <span class="toggle-icon">▶</span>')
                html_content.append('            <span class="toggle-text">Show Output</span>')
                html_content.append("        </button>")
                html_content.append(
                    f'        <div class="output-cell" id="{output_id}" style="display: none;">'
                )

                for output in outputs:
                    output_html = convert_output_to_html(output)
                    if output_html:
                        html_content.append(f"            {output_html}")

                html_content.append("        </div>")
                html_content.append("    </div>")

    html_content.append("</div>")

    # Write HTML file
    output_path = CHAPTERS_DIR / html_filename
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_content))

    return {
        "filename": html_filename,
        "title": title,
        "original_filename": notebook_path.name,
    }


def get_chapter_list():
    """Get sorted list of notebooks to process."""
    notebooks = []
    for nb_file in SOURCE_DIR.glob("*.ipynb"):
        if nb_file.name not in EXCLUDED_NOTEBOOKS:
            notebooks.append(nb_file)

    # Sort by chapter number
    notebooks.sort(key=lambda x: (extract_chapter_number(x.name), x.name))
    return notebooks


def copy_images():
    """Copy images from source directory to assets."""
    source_images = SOURCE_DIR / "images"
    if source_images.exists():
        for img_file in source_images.iterdir():
            if img_file.is_file():
                shutil.copy2(img_file, ASSETS_DIR / img_file.name)
                print(f"Copied image: {img_file.name}")


def generate_toc(chapters):
    """Generate table of contents data."""
    toc = []
    for idx, chapter in enumerate(chapters):
        toc.append(
            {"index": idx, "filename": chapter["filename"], "title": chapter["title"]}
        )
    return toc


def main():
    """Main conversion function."""
    print("Starting notebook conversion...")

    # Copy images
    print("\nCopying images...")
    copy_images()

    # Get list of notebooks
    notebooks = get_chapter_list()
    print(f"\nFound {len(notebooks)} notebooks to process")

    # Process each notebook
    chapters = []
    for idx, notebook_path in enumerate(notebooks):
        chapter_info = process_notebook(notebook_path, idx, len(notebooks))
        chapters.append(chapter_info)

    # Save TOC as JSON for JavaScript
    toc_data = generate_toc(chapters)
    toc_path = DEST_DIR / "toc.json"
    with open(toc_path, "w", encoding="utf-8") as f:
        json.dump(toc_data, f, indent=2)

    print(f"\n✓ Conversion complete! Generated {len(chapters)} chapters.")
    print(f"✓ Table of contents saved to {toc_path}")
    return chapters


if __name__ == "__main__":
    main()
