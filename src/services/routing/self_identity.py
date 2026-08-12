"""is_self_identity_question — detects "tell me about {workspace}" intent.

Shared by SourceRouter (initial routing) and SearchManager (fallback-to-web
guards) so the two layers can never define this differently. Pure string/
regex matching, no I/O, mirrors SourceRouter's own keyword-tuple style.
"""

from __future__ import annotations

import re

# Phrases that signal "who/what is this entity", not a narrower question
# (pricing, support, news, comparison, ...) about it. A false positive here
# only ever removes a web-search path / adds a caution instruction — it can
# never produce a wrong answer — so this list is deliberately generous.
_IDENTITY_PHRASES: tuple[str, ...] = (
    "tell me about", "tell us about", "more about",
    "what is", "what's", "whats",
    "who is", "who are", "who runs", "who owns", "who founded",
    "describe", "explain what",
    "information about", "information on",
    "company profile", "company info", "company information", "company overview",
    "what does", "what do you know about",
)


# Max characters allowed between an identity phrase and the workspace-name
# mention (in either order) for them to count as "adjacent" — roughly a
# small connector like "the" or "some", not an unrelated clause. Keeps
# "Tell me about Ha-Shem" / "Ha-Shem company profile" matching while
# rejecting "What is Ha-Shem's pricing for STAAS?" (possessive — excluded
# separately below) and "...latest news about Ha-Shem partners" (the
# identity phrase and the name aren't part of the same clause).
_MAX_ADJACENT_GAP = 15


def is_self_identity_question(question: str, workspace_name: str | None) -> bool:
    """True if *question* asks "about" *workspace_name* itself.

    Requires the workspace's own name to appear as a whole word/phrase
    (not possessive — "Ha-Shem's" doesn't count, that's a question about
    something *of* the workspace, not the workspace itself) immediately
    adjacent to one of the generic identity phrases above, in either
    order. A specific question that merely mentions the workspace
    (pricing, support, comparison, unrelated news) does NOT trigger this.
    Returns False for empty/None input on either side, never raises.
    """
    if not question or not workspace_name:
        return False
    name = workspace_name.strip().lower()
    if not name:
        return False
    q = question.lower()
    name_match = re.search(rf"\b{re.escape(name)}\b(?!'s\b)", q)
    if name_match is None:
        return False
    for phrase in _IDENTITY_PHRASES:
        for phrase_match in re.finditer(re.escape(phrase), q):
            if phrase_match.end() <= name_match.start():
                gap = q[phrase_match.end():name_match.start()]
            elif name_match.end() <= phrase_match.start():
                gap = q[name_match.end():phrase_match.start()]
            else:
                continue  # overlapping matches, not a meaningful pairing
            if len(gap.strip()) <= _MAX_ADJACENT_GAP:
                return True
    return False
