#!/usr/bin/env python3
"""
Generate separate HTML files for each chapter with pure HTML/CSS navigation.
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
    "2_Linear_regression_summary.ipynb",
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

# Initialize markdown converter with proper list handling
md = markdown.Markdown(
    extensions=["codehilite", "fenced_code", "tables", "nl2br", "sane_lists"]
)


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


def fix_list_formatting(text):
    """Fix list formatting to ensure proper markdown list recognition and nesting."""
    lines = text.split("\n")
    fixed_lines = []
    prev_line_ended_with_colon = False
    prev_list_indent = -1

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if line starts with list marker
        list_match = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.+)", line)

        if list_match:
            indent = len(list_match.group(1))
            content = list_match.group(3)

            # If previous list item ended with colon, nest subsequent items
            if prev_line_ended_with_colon and indent <= prev_list_indent:
                # This should be nested - add 2 spaces of indentation
                fixed_lines.append(" " * (prev_list_indent + 2) + line.lstrip())
                prev_list_indent = prev_list_indent + 2
            else:
                # Ensure blank line before list if needed
                if (
                    fixed_lines
                    and fixed_lines[-1].strip()
                    and not fixed_lines[-1].strip().endswith(":")
                ):
                    # Check if previous line was a list
                    prev_was_list = False
                    if len(fixed_lines) > 0:
                        prev_line = fixed_lines[-1]
                        if re.match(r"^\s*[-*+]|\d+\.", prev_line):
                            prev_was_list = False  # Continue same list
                        else:
                            prev_was_list = True

                    if prev_was_list:
                        fixed_lines.append("")

                fixed_lines.append(line)
                prev_list_indent = indent

            # Check if this line ends with colon (indicates nested content follows)
            prev_line_ended_with_colon = content.rstrip().endswith(":")
        else:
            # Not a list item
            if stripped:
                prev_line_ended_with_colon = False
                prev_list_indent = -1
            fixed_lines.append(line)

        i += 1

    return "\n".join(fixed_lines)


def markdown_to_html(markdown_text):
    """Convert markdown to HTML while preserving LaTeX."""
    import uuid

    latex_map = {}
    text = markdown_text

    # Fix list formatting first
    text = fix_list_formatting(text)

    # Protect equation blocks (equation*, equation)
    equation_pattern = r"\\begin\{equation\*?\}.*?\\end\{equation\*?\}"
    for match in reversed(list(re.finditer(equation_pattern, text, re.DOTALL))):
        unique_id = str(uuid.uuid4()).replace("-", "")
        placeholder = f"<!--LATEX_EQ_{unique_id}-->"
        latex_map[placeholder] = match.group(0)
        start, end = match.span()
        text = text[:start] + "\n\n" + placeholder + "\n\n" + text[end:]

    # Protect align blocks
    align_pattern = r"\\begin\{align\*?\}.*?\\end\{align\*?\}"
    for match in reversed(list(re.finditer(align_pattern, text, re.DOTALL))):
        unique_id = str(uuid.uuid4()).replace("-", "")
        placeholder = f"<!--LATEX_ALIGN_{unique_id}-->"
        latex_map[placeholder] = match.group(0)
        start, end = match.span()
        text = text[:start] + "\n\n" + placeholder + "\n\n" + text[end:]

    # Protect display math ($$...$$)
    display_pattern = r"\$\$.*?\$\$"
    for match in reversed(list(re.finditer(display_pattern, text, re.DOTALL))):
        unique_id = str(uuid.uuid4()).replace("-", "")
        placeholder = f"<!--LATEX_DISPLAY_{unique_id}-->"
        latex_map[placeholder] = match.group(0)
        start, end = match.span()
        text = text[:start] + "\n\n" + placeholder + "\n\n" + text[end:]

    # Protect inline math
    inline_pattern = r"(?<!\$)\$[^$\n]+\$(?!\$)"
    for match in reversed(list(re.finditer(inline_pattern, text))):
        unique_id = str(uuid.uuid4()).replace("-", "")
        placeholder = f"<!--LATEX_INLINE_{unique_id}-->"
        latex_map[placeholder] = match.group(0)
        start, end = match.span()
        text = text[:start] + placeholder + text[end:]

    md.reset()
    html = md.convert(text)

    # Restore LaTeX blocks
    for placeholder, latex_content in latex_map.items():
        html = html.replace(placeholder, latex_content)

    # Clean up paragraph wrapping around LaTeX blocks
    # Remove <p> tags wrapping equation, align, or display math blocks
    html = re.sub(
        r"<p>\s*(\\begin\{(?:equation|align)\*?\}.*?\\end\{(?:equation|align)\*?\})\s*</p>",
        r"\1",
        html,
        flags=re.DOTALL,
    )

    # Remove <p> tags wrapping display math ($$...$$)
    html = re.sub(r"<p>\s*(\$\$.*?\$\$)\s*</p>", r"\1", html, flags=re.DOTALL)

    # Remove <br /> tags that appear inside LaTeX blocks
    html = re.sub(
        r"(\\begin\{(?:equation|align)\*?\}[^<]*?)\\<br\s*/?\>\\n([^<]*?\\end\{(?:equation|align)\*?\})",
        r"\1\n\2",
        html,
        flags=re.DOTALL,
    )

    # Also handle multi-line LaTeX blocks with <br /> between lines
    html = re.sub(
        r"(\\begin\{(?:equation|align)\*?\}.*?)\\<br\s*/?\>\\n(.*?\\end\{(?:equation|align)\*?\})",
        r"\1\n\2",
        html,
        flags=re.DOTALL,
    )

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


def generate_toc_html(chapters_data, current_index):
    """Generate TOC HTML for sidebar with collapsible chapters."""
    toc_html = []

    # Group all sections under "Chapter 1: Linear Regression"
    toc_html.append('            <div class="toc-chapter">')
    toc_html.append(
        '                <input type="checkbox" id="toc-chapter-1" class="toc-chapter-toggle" checked>'
    )
    toc_html.append(
        '                <label for="toc-chapter-1" class="toc-chapter-label">'
    )
    toc_html.append('                    <span class="toc-chapter-icon">▼</span>')
    toc_html.append("                    <span>Chapter 1: Linear Regression</span>")
    toc_html.append("                </label>")
    toc_html.append('                <div class="toc-sections">')

    for idx, (chapter_id, title, filename) in enumerate(chapters_data):
        section_num = idx + 1
        active_class = (
            ' class="toc-item active"' if idx == current_index else ' class="toc-item"'
        )
        toc_html.append(
            f'                    <a href="{filename}"{active_class}>Section {section_num}: {escape(title)}</a>'
        )

    toc_html.append("                </div>")
    toc_html.append("            </div>")

    return "\n".join(toc_html)


def process_notebook(notebook_path, chapter_id, chapters_data):
    """Process a notebook and generate a complete HTML page."""
    print(f"Processing {notebook_path.name}...")

    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    title = get_chapter_title(notebook_path)
    html_filename = f"chapter-{chapter_id}.html"

    # Build HTML
    html_parts = []
    html_parts.append("<!DOCTYPE html>")
    html_parts.append('<html lang="en">')
    html_parts.append("<head>")
    html_parts.append('    <meta charset="UTF-8">')
    html_parts.append(
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">'
    )
    html_parts.append(f"    <title>{escape(title)}</title>")
    html_parts.append('    <link rel="stylesheet" href="../styles.css">')
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
    html_parts.append(generate_toc_html(chapters_data, chapter_id))
    html_parts.append("        </nav>")
    html_parts.append("    </div>")

    # Main content area
    html_parts.append('    <div class="main-content">')
    html_parts.append('        <div class="content-pane">')
    html_parts.append(f'            <div class="chapter-content">')
    html_parts.append(f'                <h1 class="chapter-title">{escape(title)}</h1>')

    cell_counter = 0
    for cell in nb.get("cells", []):
        cell_type = cell.get("cell_type", "")
        source = "".join(cell.get("source", []))

        if not source.strip() and cell_type == "markdown":
            continue

        if cell_type == "markdown":
            html = markdown_to_html(source)
            html_parts.append(
                f'                <div class="markdown-cell">{html}</div>'
            )

        elif cell_type == "code":
            # Skip code cells and outputs entirely
            continue

    html_parts.append("            </div>")
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

    # Write HTML file
    output_path = CHAPTERS_DIR / html_filename
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    return html_filename, title


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


def generate_index_html(chapters_data):
    """Generate index.html with TOC."""
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
    html_parts.append('            <div class="toc-chapter">')
    html_parts.append(
        '                <input type="checkbox" id="toc-chapter-1-index" class="toc-chapter-toggle" checked>'
    )
    html_parts.append(
        '                <label for="toc-chapter-1-index" class="toc-chapter-label">'
    )
    html_parts.append('                    <span class="toc-chapter-icon">▼</span>')
    html_parts.append("                    <span>Chapter 1: Linear Regression</span>")
    html_parts.append("                </label>")
    html_parts.append('                <div class="toc-sections">')
    for idx, (chapter_id, title, filename) in enumerate(chapters_data):
        section_num = idx + 1
        html_parts.append(
            f'                    <a href="chapters/{filename}" class="toc-item">Section {section_num}: {escape(title)}</a>'
        )
    html_parts.append("                </div>")
    html_parts.append("            </div>")
    html_parts.append("        </nav>")
    html_parts.append("    </div>")

    # Main content area - welcome message
    html_parts.append('    <div class="main-content">')
    html_parts.append('        <div class="content-pane">')
    html_parts.append('            <div class="chapter-content">')
    html_parts.append(
        '                <h1 class="chapter-title">Linear Regression</h1>'
    )
    html_parts.append(
        "                <p>Select a chapter from the table of contents to begin reading.</p>"
    )
    html_parts.append("            </div>")
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

    output_path = DEST_DIR / "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    print(f"✓ Generated index.html")


def generate_all():
    """Generate all HTML files."""
    print("Generating multi-page HTML...")

    copy_images()

    notebooks = get_chapter_list()
    print(f"Found {len(notebooks)} notebooks to process")

    chapters_data = []
    for idx, notebook_path in enumerate(notebooks):
        html_filename, title = process_notebook(notebook_path, idx, [])
        chapters_data.append((idx, title, html_filename))

    # Regenerate all chapters with full TOC data
    print("\nRegenerating chapters with full TOC...")
    for idx, notebook_path in enumerate(notebooks):
        process_notebook(notebook_path, idx, chapters_data)

    # Generate index.html
    generate_index_html(chapters_data)

    print(f"\n✓ Generated {len(chapters_data)} chapter pages + index.html")


if __name__ == "__main__":
    generate_all()
