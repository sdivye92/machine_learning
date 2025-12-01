// Global state
let currentChapterIndex = 0;
let chapters = [];

// Load table of contents and initialize
async function init() {
    try {
        const response = await fetch('toc.json');
        if (!response.ok) {
            console.error('Failed to load TOC');
            return;
        }
        
        chapters = await response.json();
        populateTOC();
        
        // Load first chapter by default
        if (chapters.length > 0) {
            loadChapter(0);
        }
    } catch (error) {
        console.error('Error loading TOC:', error);
    }
}

// Populate table of contents
function populateTOC() {
    const tocElement = document.getElementById('toc');
    if (!tocElement) return;
    
    tocElement.innerHTML = '';
    
    chapters.forEach((chapter, index) => {
        const tocItem = document.createElement('a');
        tocItem.href = '#';
        tocItem.className = 'toc-item';
        tocItem.textContent = chapter.title;
        tocItem.onclick = (e) => {
            e.preventDefault();
            loadChapter(index);
        };
        tocElement.appendChild(tocItem);
    });
}

// Load chapter content
async function loadChapter(index) {
    if (index < 0 || index >= chapters.length) return;
    
    currentChapterIndex = index;
    const chapter = chapters[index];
    const contentPane = document.getElementById('contentPane');
    
    if (!contentPane) return;
    
    // Update active TOC item
    updateActiveTOCItem(index);
    
    // Show loading
    contentPane.innerHTML = '<div class="loading">Loading</div>';
    
    try {
        const response = await fetch(`chapters/${chapter.filename}`);
        if (!response.ok) {
            throw new Error('Failed to load chapter');
        }
        
        const html = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Extract chapter content
        const chapterContent = doc.querySelector('.chapter-content');
        if (chapterContent) {
            contentPane.innerHTML = chapterContent.innerHTML;
            
            // Re-render MathJax
            if (window.MathJax && window.MathJax.typesetPromise) {
                window.MathJax.typesetPromise().catch((err) => {
                    console.error('MathJax rendering error:', err);
                });
            }
        } else {
            contentPane.innerHTML = '<div class="loading">Error loading chapter content</div>';
        }
    } catch (error) {
        console.error('Error loading chapter:', error);
        contentPane.innerHTML = '<div class="loading">Error loading chapter</div>';
    }
}

// Update active TOC item
function updateActiveTOCItem(index) {
    const tocItems = document.querySelectorAll('.toc-item');
    tocItems.forEach((item, i) => {
        if (i === index) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

// Initialize code and output toggles using event delegation (set up once)
let togglesInitialized = false;

function initializeToggles() {
    if (togglesInitialized) return;
    
    const contentPane = document.getElementById('contentPane');
    if (contentPane) {
        // Use event delegation for code toggles
        contentPane.addEventListener('click', function(e) {
            if (e.target.closest('.code-toggle')) {
                const button = e.target.closest('.code-toggle');
                const onclickAttr = button.getAttribute('onclick');
                if (onclickAttr) {
                    const match = onclickAttr.match(/toggleCodeCell\(['"]([^'"]+)['"]\)/);
                    if (match) {
                        e.preventDefault();
                        toggleCodeCell(match[1], button);
                    }
                }
            } else if (e.target.closest('.output-toggle')) {
                const button = e.target.closest('.output-toggle');
                const onclickAttr = button.getAttribute('onclick');
                if (onclickAttr) {
                    const match = onclickAttr.match(/toggleOutput\(['"]([^'"]+)['"]\)/);
                    if (match) {
                        e.preventDefault();
                        toggleOutput(match[1], button);
                    }
                }
            }
        });
        togglesInitialized = true;
    }
}

// Toggle code cell visibility
function toggleCodeCell(cellId, button) {
    const cell = document.getElementById(cellId);
    if (!cell || !button) return;
    
    const isHidden = cell.style.display === 'none';
    cell.style.display = isHidden ? 'block' : 'none';
    
    if (isHidden) {
        button.classList.add('expanded');
        const toggleText = button.querySelector('.toggle-text');
        if (toggleText) toggleText.textContent = 'Hide Code';
    } else {
        button.classList.remove('expanded');
        const toggleText = button.querySelector('.toggle-text');
        if (toggleText) toggleText.textContent = 'Show Code';
    }
}

// Toggle output visibility
function toggleOutput(outputId, button) {
    const output = document.getElementById(outputId);
    if (!output || !button) return;
    
    const isHidden = output.style.display === 'none';
    output.style.display = isHidden ? 'block' : 'none';
    
    if (isHidden) {
        button.classList.add('expanded');
        const toggleText = button.querySelector('.toggle-text');
        if (toggleText) toggleText.textContent = 'Hide Output';
    } else {
        button.classList.remove('expanded');
        const toggleText = button.querySelector('.toggle-text');
        if (toggleText) toggleText.textContent = 'Show Output';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    init();
    // Initialize toggles for event delegation
    initializeToggles();
});
