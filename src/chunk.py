# filepath: src/chunk.py
from typing import List

def split_into_semantic_chunks(
    cleaned_text: str, 
    max_chunk_size: int = 600
) -> List[str]:
    """
    Splits pristine markdown text into manageable blocks by paragraph.
    Ensures structural sections stick together without breaking sentences mid-thought.
    """
    if not cleaned_text:
        return []

    # Split text by paragraphs to preserve natural thought structures
    paragraphs = cleaned_text.split("\n\n")
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        # If adding this paragraph keeps us within limits, merge it
        if len(current_chunk) + len(paragraph) <= max_chunk_size:
            current_chunk += ("\n\n" if current_chunk else "") + paragraph
        else:
            # Save the completed chunk
            if current_chunk:
                chunks.append(current_chunk)
            
            # Start a new chunk context
            if len(paragraph) > max_chunk_size:
                # If a single paragraph is massive, break it safely by character limits
                chunks.append(paragraph[:max_chunk_size])
                current_chunk = paragraph[max_chunk_size:]
            else:
                current_chunk = paragraph

    # Don't forget to catch the final trailing block
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks