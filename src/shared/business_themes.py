"""BUSINESS_THEMES — broad business-transformation questions mapped to a
cluster of relevant products.

``PRODUCT_REGISTRY`` (see ``product_registry.py``) handles the case where a
question signals interest in *one* specific product, directly or by its own
intent keywords ("we need visitor check-in" -> V-Login). It does not cover
broader questions that don't name any single product's own keywords but
imply several at once — "we want to modernize our HR operations" mentions
none of ZivaAIRA/STAAS/Havis Vacay/PayCheq/WeCare/Havis iReport's individual
keywords, yet all of them are relevant.

This is a separate, small, additive registry for exactly that case. Each
theme is a keyword-matched phrase (same substring-matching philosophy as
everywhere else in the routing layer) resolving to a cluster of real
products from PRODUCT_REGISTRY, with an optional *primary* recommendation.
``primary=None`` means the cluster is a set of parallel, equally-weighted
recommendations rather than one dominant solution (e.g. broad digital
transformation touching many departments at once) — set explicitly, not
inferred, so the "primary vs. complementary" framing in a generated answer
is grounded in this data rather than guessed by the model at generation
time.

``ProductRouter.classify()`` checks this only as a fallback, after direct
product name/keyword matching finds nothing — an explicit product mention
always wins. Adding a new theme (or updating an existing one as products are
added) means editing this dict; no other code changes are required.
"""

from __future__ import annotations

from typing import TypedDict


class BusinessTheme(TypedDict):
    keywords: tuple[str, ...]
    products: tuple[str, ...]
    primary: str | None


BUSINESS_THEMES: dict[str, BusinessTheme] = {
    "visitor_onboarding": {
        "keywords": (
            "securely onboard visitors", "onboard visitors securely",
            "visitor onboarding", "onboarding visitors",
        ),
        "products": ("V-Login", "SPIDIFY"),
        "primary": "V-Login",
    },
    "hr_modernization": {
        "keywords": (
            "modernize hr", "modernise hr", "modernize our hr",
            "modernise our hr", "hr operations", "hr transformation",
            "transform hr", "improve hr operations", "hr digital transformation",
        ),
        "products": ("ZivaAIRA", "STAAS", "Havis Vacay", "PayCheq", "WeCare", "Havis iReport"),
        "primary": "ZivaAIRA",
    },
    "digital_transformation": {
        "keywords": (
            "digitizing our company", "digitising our company",
            "digitize our company", "digitise our company",
            "digital transformation", "digitize our business",
            "digitise our business", "going digital", "digitize operations",
            "digitise operations", "digitize our operations",
        ),
        "products": (
            "ZivaAIRA", "STAAS", "Havis Vacay", "PayCheq", "WeCare",
            "Havis iReport", "Havis Xpend",
        ),
        # No single dominant product for company-wide digitization — each
        # covers a distinct department/function, so all are presented as
        # parallel recommendations rather than one primary + complements.
        "primary": None,
    },
}
