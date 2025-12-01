#!/usr/bin/env python3
"""
Generate a single HTML file with all chapters embedded, using pure HTML/CSS.
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
ASSETS_DIR = DEST_DIR / "assets" / "images"

# Create directories
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Initialize markdown converter
md = markdown.Markdown(extensions=["codehilite", "fenced_code", "tables", "nl2br"])


def extract_chapter_number(filename):
    """Extract chapter number from filename for sorting."""
    match = re.match(r"^(\d+)", filename)
    if match:
        return int(match.group(1))
    return 999


def get_chapter_title(notebook_path):
    """Extract title from first markdown cell."""
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "markdown":
            source = "".join(cell.get("source", []))
            lines = source.strip().split("\n")
            for line in lines:
                if line.startswith("#"):
                    title = re.sub(r"^#+\s*", "", line).strip()
                    if title:
                        return title

    return notebook_path.stem.replace("_", " ").title()


def markdown_to_html(markdown_text):
    """Convert markdown to HTML while preserving LaTeX."""
    import uuid

    latex_map = {}
    text = markdown_text

    # Protect align blocks first
    align_pattern = r"\\begin\{align\*?\}.*?\\end\{align\*?\}"
    for match in reversed(list(re.finditer(align_pattern, text, re.DOTALL))):
        unique_id = str(uuid.uuid4()).replace("-", "")
        placeholder = f"<!--LATEX_{unique_id}-->"
        latex_map[placeholder] = match.group(0)
        start, end = match.span()
        text = text[:start] + placeholder + text[end:]

    # Protect display math
    display_pattern = r"\$\$.*?\$\$"
    for match in reversed(list(re.finditer(display_pattern, text, re.DOTALL))):
        unique_id = str(uuid.uuid4()).replace("-", "")
        placeholder = f"<!--LATEX_{unique_id}-->"
        latex_map[placeholder] = match.group(0)
        start, end = match.span()
        text = text[:start] + placeholder + text[end:]

    # Protect inline math
    inline_pattern = r"(?<!\$)\$[^$\n]+\$(?!\$)"
    for match in reversed(list(re.finditer(inline_pattern, text))):
        unique_id = str(uuid.uuid4()).replace("-", "")
        placeholder = f"<!--LATEX_{unique_id}-->"
        latex_map[placeholder] = match.group(0)
        start, end = match.span()
        text = text[:start] + placeholder + text[end:]

    md.reset()
    html = md.convert(text)

    for placeholder, latex_content in latex_map.items():
        html = html.replace(placeholder, latex_content)

    return html


def convert_output_to_html(output):
    """Convert notebook output to HTML."""
    output_type = output.get("output_type", "")

    if output_type == "stream":
        text = "".join(output.get("text", []))
        return f'<pre class="output-text">{escape(text)}</pre>'

    elif output_type == "execute_result" or output_type == "display_data":
        data = output.get("data", {})

        if "text/plain" in data:
            text = "".join(data["text/plain"])
            return f'<pre class="output-text">{escape(text)}</pre>'

        if "text/html" in data:
            html = "".join(data["text/html"])
            return f'<div class="output-html">{html}</div>'

        if "image/png" in data:
            img_data = data["image/png"]
            if isinstance(img_data, str):
                return f'<img src="data:image/png;base64,{img_data}" class="output-image" alt="Output image">'

        if "text/latex" in data:
            latex = "".join(data["text/latex"])
            return f'<div class="output-latex">$${latex}$$</div>'

    return ""


def process_notebook(notebook_path, chapter_id):
    """Process a notebook and return its HTML content."""
    print(f"Processing {notebook_path.name}...")

    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    title = get_chapter_title(notebook_path)
    html_content = []
    html_content.append(f'<section id="chapter-{chapter_id}" class="chapter-content">')
    html_content.append(f'    <h1 class="chapter-title">{escape(title)}</h1>')

    cell_counter = 0
    for cell in nb.get("cells", []):
        cell_type = cell.get("cell_type", "")
        source = "".join(cell.get("source", []))

        if not source.strip() and cell_type == "markdown":
            continue

        if cell_type == "markdown":
            html = markdown_to_html(source)
            html_content.append(f'    <div class="markdown-cell">{html}</div>')

        elif cell_type == "code":
            cell_id = f"code-{chapter_id}-{cell_counter}"
            cell_counter += 1

            # Code cell with checkbox toggle
            html_content.append('    <div class="code-cell-container">')
            html_content.append(
                f'        <input type="checkbox" id="{cell_id}" class="code-toggle-checkbox">'
            )
            html_content.append(f'        <label for="{cell_id}" class="code-toggle">')
            html_content.append('            <span class="toggle-icon">▶</span>')
            html_content.append(
                '            <span class="toggle-text">Show Code</span>'
            )
            html_content.append("        </label>")
            html_content.append(f'        <div class="code-cell">')
            html_content.append(
                f'            <pre><code class="language-python">{escape(source)}</code></pre>'
            )
            html_content.append("        </div>")
            html_content.append("    </div>")

            # Outputs
            outputs = cell.get("outputs", [])
            if outputs:
                output_id = f"output-{chapter_id}-{cell_counter-1}"
                html_content.append('    <div class="output-container">')
                html_content.append(
                    f'        <input type="checkbox" id="{output_id}" class="output-toggle-checkbox">'
                )
                html_content.append(
                    f'        <label for="{output_id}" class="output-toggle">'
                )
                html_content.append('            <span class="toggle-icon">▶</span>')
                html_content.append(
                    '            <span class="toggle-text">Show Output</span>'
                )
                html_content.append("        </label>")
                html_content.append(f'        <div class="output-cell">')

                for output in outputs:
                    output_html = convert_output_to_html(output)
                    if output_html:
                        html_content.append(f"            {output_html}")

                html_content.append("        </div>")
                html_content.append("    </div>")

    html_content.append("</section>")
    return "\n".join(html_content), title


def get_chapter_list():
    """Get sorted list of notebooks to process."""
    notebooks = []
    for nb_file in SOURCE_DIR.glob("*.ipynb"):
        if nb_file.name not in EXCLUDED_NOTEBOOKS:
            notebooks.append(nb_file)

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


def generate_index_html():
    """Generate single-page HTML with all chapters."""
    print("Generating single-page HTML...")

    copy_images()

    notebooks = get_chapter_list()
    print(f"Found {len(notebooks)} notebooks to process")

    # Build HTML
    html_parts = []
    html_parts.append("<!DOCTYPE html>")
    html_parts.append('<html lang="en">')
    html_parts.append("<head>")
    html_parts.append('    <meta charset="UTF-8">')
    html_parts.append(
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">'
    )
    html_parts.append("    <title>Linear Regression</title>")
    html_parts.append('    <link rel="stylesheet" href="styles.css">')
    html_parts.append(
        '    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>'
    )
    html_parts.append(
        '    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>'
    )
    html_parts.append("    <script>")
    html_parts.append("        window.MathJax = {")
    html_parts.append("            tex: {")
    html_parts.append("                inlineMath: [['$', '$']],")
    html_parts.append("                displayMath: [['$$', '$$']]")
    html_parts.append("            }")
    html_parts.append("        };")
    html_parts.append("    </script>")
    html_parts.append(
        '    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism.min.css">'
    )
    html_parts.append("</head>")
    html_parts.append("<body>")

    # Sidebar with TOC
    html_parts.append('    <div class="sidebar">')
    html_parts.append('        <div class="sidebar-header">')
    html_parts.append("            <h2>Table of Contents</h2>")
    html_parts.append("        </div>")
    html_parts.append('        <nav class="toc">')

    chapters_data = []
    for idx, notebook_path in enumerate(notebooks):
        chapter_id = idx
        chapter_html, title = process_notebook(notebook_path, chapter_id)
        chapters_data.append((chapter_id, title, chapter_html))

        # Add TOC item
        html_parts.append(
            f'            <a href="#chapter-{chapter_id}" class="toc-item">{escape(title)}</a>'
        )

    html_parts.append("        </nav>")
    html_parts.append("    </div>")

    # Main content area
    html_parts.append('    <div class="main-content">')
    html_parts.append('        <div class="content-pane">')

    # Add all chapters
    for chapter_id, title, chapter_html in chapters_data:
        html_parts.append(chapter_html)

    html_parts.append("        </div>")
    html_parts.append("    </div>")

    html_parts.append(
        '    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>'
    )
    html_parts.append(
        '    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>'
    )
    html_parts.append("</body>")
    html_parts.append("</html>")

    # Write to index.html
    output_path = DEST_DIR / "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    print(f"✓ Generated single-page HTML: {output_path}")


if __name__ == "__main__":
    generate_index_html()
