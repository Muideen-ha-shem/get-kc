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

# A public user asking about "this company"/"the platform"/etc. never
# needs to say the workspace's own name — these deictic phrases mean the
# workspace itself, full stop, regardless of whether workspace_name is
# even known. Live-confirmed bug: "Tell me the core values of this
# company" (no name mentioned) was answered as if it were about SPIDIFY
# (the last-discussed product) instead of the host workspace — session
# pronoun resolution was also rewriting "this company" into "this SPIDIFY
# company" before this function ever saw it (see session_context.py's
# _SELF_REFERENTIAL_NOUNS exclusion, which is the other half of this fix).
_DEICTIC_SELF_REFERENCES: tuple[str, ...] = (
    "this company", "this platform", "this organization", "this organisation", "this business",
    "that company", "that platform", "that organization", "that organisation", "that business",
    "the company", "the platform", "your company", "your platform",
    "you guys",
)


def is_self_identity_question(question: str, workspace_name: str | None) -> bool:
    """True if *question* asks "about" the workspace itself.

    Two independent ways to match:
    1. A deictic self-reference ("this company", "the platform", "your
       company", ...) — always means the workspace, never requires
       ``workspace_name`` to be known or mentioned.
    2. The workspace's own name appears as a whole word/phrase (not
       possessive — "Ha-Shem's" doesn't count, that's a question about
       something *of* the workspace) immediately adjacent to one of the
       generic identity phrases above, in either order.

    A specific question that merely mentions the workspace (pricing,
    support, comparison, unrelated news) does NOT trigger this. Returns
    False for empty input, never raises.
    """
    if not question:
        return False
    q = question.lower()

    if any(phrase in q for phrase in _DEICTIC_SELF_REFERENCES):
        return True

    if not workspace_name:
        return False
    name = workspace_name.strip().lower()
    if not name:
        return False
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
