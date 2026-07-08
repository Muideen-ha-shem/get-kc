import re

def intensive_clean_markdown(raw_markdown: str) -> str:
    """
    Strips cookie notices, structural boilerplate, navigation text,
    and formatting noise to isolate the pure content of the page.
    """
    if not raw_markdown:
        return ""

    text = raw_markdown

    # 1. REMOVE COOKIE & PRIVACY CONSENT BLOCKS (HARDENED PATTERNS)
    cookie_patterns = [
        # Core initial banner text blocks
        r"(?i)we value your privacy.*?(accept all|reject all|customise consent)",
        r"(?i)at ha-shem limited we use cookies.*?show more",
        r"(?i)the cookies that are categorised as.*?stored on your browser",
        r"(?i)by continuing to use our website you are deemed.*?privacy policy",
        r"(?i)consent preferences.*?necessary.*?functional.*?analytics",
        
        # Targets detailed category definitions (with or without word duplication)
        r"(?i)analytical( cookies are used to understand.*?no cookies to display\.)?",
        r"(?i)performance( performance)? cookies are used to understand.*?no cookies to display\.",
        r"(?i)advertisement( advertisement)? cookies are used to provide.*?no cookies to display\.",
        
        # Catch-all for any standalone block discussing performance index / ad campaigns text
        r"(?i)performance cookies are used to understand and analyse.*?no cookies to display\.",
        r"(?i)advertisement cookies are used to provide visitors.*?no cookies to display\.",
        
        # Clears lingering cookie dashboard/preference control text strings
        r"(?i)reject all\s+save my preferences\s+accept all",
        r"(?i)cookie policy.*?privacy notice.*?manage choices"
    ]
    
    for pattern in cookie_patterns:
        text = re.sub(pattern, "", text, flags=re.DOTALL)

    # 2. REMOVE IMAGES AND LINK URL TRASH
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[\s*(video|embed|youtube|vimeo)\s*\].*?\n', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'\[\]\(.*?\)', '', text)
    text = re.sub(r'\[.*?\]\(\)', '', text)

    # 3. STRIP COMMON HEADER/FOOTER METADATA OR LAYOUT REMNANTS
    text = re.sub(r'^\s*Home\s*/\s*.*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'\|[\s\-|\+]*\|', '', text)
    
    # 4. LINE-BY-LINE TRIMMING AND FRAGMENT FILTERING
    lines = text.split('\n')
    cleaned_lines = []
    
    # Expanded list of exact standalone garbage phrases / button fragments to completely delete
    boilerplate_fragments = {
        "read more", "click here", "submit", "learn more", "close", "reject all", 
        "accept all", "customise", "show more", "privacy policy", "cookies policy",
        "save my preferences", "performance", "advertisement", 
        "no whatsapp number found!", "cookie settings"  # Added your newly flagged elements here
    }
    
    for line in lines:
        line_stripped = line.strip()
        
        # Skip empty lines or structural separation lines
        if line_stripped in ['|', '-', '_', '•', '»', '***', '---', '']:
            continue
            
        # Skip any line that matches our exact boilerplate word filters (case-insensitive)
        if line_stripped.lower() in boilerplate_fragments:
            continue
            
        # Extra safety: check if the string contains the explicit widget warnings anywhere inside it
        if "no whatsapp number found!" in line_stripped.lower() or "cookie settings" in line_stripped.lower():
            continue
            
        cleaned_lines.append(line_stripped)
        
    text = '\n'.join(cleaned_lines)

    # 5. WHITE SPACE AND NEWLINE REFACTORING
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    
    return text.strip()
