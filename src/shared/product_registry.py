"""PRODUCT_REGISTRY — the single source of truth for every Ha-Shem product
HavisIQ knows about.

Both the crawl/metadata pipeline (``scripts/product_metadata.py``) and the
retrieval-time classifier (``src.services.routing.ProductRouter``) read from
this one table instead of maintaining separate, hand-synced copies of each
product's URL, aliases, and intent keywords. Adding product #12 means adding
one entry here — nothing else needs to change.

Two URL-matching shapes are supported, since not every product lives on its
own domain:

* ``path_prefix is None`` — the whole domain is dedicated to this product
  (SPIDIFY on havisspidify.com, ZivaAIRA on aira.havis360.com).
* ``path_prefix`` set — the product is a subpage of a shared domain
  (the newer HAVIS-360 products, all under ha-shem.com/HAVIS-360/<slug>/).
  Matching is domain + path-prefix together, so unrelated ha-shem.com pages
  (e.g. "/about") still correctly fall through to no product match.
"""

from __future__ import annotations

from typing import TypedDict


class ProductInfo(TypedDict):
    url: str
    domain: str
    path_prefix: str | None
    category: str
    business_problem: str
    solution_type: str
    aliases: tuple[str, ...]
    keywords: tuple[str, ...]


PRODUCT_REGISTRY: dict[str, ProductInfo] = {
    "SPIDIFY": {
        "url": "https://havisspidify.com/",
        "domain": "havisspidify.com",
        "path_prefix": None,
        "category": "Identity Verification",
        "business_problem": "Identity verification, KYC, and secure user onboarding",
        "solution_type": "Identity & Access",
        "aliases": ("spidify",),
        "keywords": (
            "identity verification", "verify users", "verify identity",
            "user verification", "identity validation",
            "kyc", "know your customer",
            "secure access", "user authentication", "authentication",
            "compliance verification", "onboarding users", "onboard users",
            "verify customers", "customer verification", "secure onboarding",
            "document verification", "id validation",
        ),
    },
    "ZivaAIRA": {
        "url": "https://aira.havis360.com/",
        "domain": "aira.havis360.com",
        "path_prefix": None,
        "category": "HR Recruitment",
        "business_problem": "AI-driven recruitment, hiring automation, and candidate screening",
        "solution_type": "HR & Recruitment",
        "aliases": ("zivaaira", "ziva aira", "aira"),
        "keywords": (
            "recruitment", "recruit", "recruiting", "recruiter",
            "hiring", "hire", "hiring automation",
            "talent acquisition", "talent management",
            "hr management", "human resources", "hr workflow",
            "applicant tracking", "job applicants", "candidate screening",
            "interview scheduling", "onboarding employees", "onboard staff",
            "workforce management", "employee onboarding",
            "ai interviews", "resume scoring",
        ),
    },
    # ------------------------------------------------------------------
    # HAVIS-360 catalog — subpages of ha-shem.com, matched by path prefix.
    # ------------------------------------------------------------------
    "V-Login": {
        "url": "https://ha-shem.com/HAVIS-360/v-login/",
        "domain": "ha-shem.com",
        "path_prefix": "/havis-360/v-login",
        "category": "Visitor & Access Management",
        "business_problem": "Visitor management, check-in, and secure visitor authentication",
        "solution_type": "Access & Identity",
        "aliases": ("v-login", "vlogin", "v login"),
        # Deliberately does NOT include SPIDIFY's "identity verification" /
        # "secure onboarding" keywords — those phrases are already SPIDIFY's
        # and are genuinely ambiguous between the two; "visitor"-scoped
        # phrasing is what actually distinguishes V-Login's intent.
        "keywords": (
            "visitor management", "visitor check-in", "visitor checkin",
            "visitor authentication", "check in visitors", "visitor check in",
            "guest management", "front desk check-in", "front desk checkin",
        ),
    },
    "STAAS": {
        "url": "https://ha-shem.com/HAVIS-360/staas/",
        "domain": "ha-shem.com",
        "path_prefix": "/havis-360/staas",
        "category": "Workforce Attendance",
        "business_problem": "Staff attendance, clock-in/out, and time tracking",
        "solution_type": "Workforce Management",
        "aliases": ("staas",),
        "keywords": (
            "attendance", "clock in", "clock-in", "clock out", "clock-out",
            "staff attendance", "remote attendance", "hybrid attendance",
            "time tracking", "attendance tracking", "employee attendance",
        ),
    },
    "WeCare": {
        "url": "https://ha-shem.com/HAVIS-360/wecare/",
        "domain": "ha-shem.com",
        "path_prefix": "/havis-360/wecare",
        "category": "Customer & Employee Support",
        "business_problem": "Customer support, help desk, and incident management",
        "solution_type": "Support & Service",
        "aliases": ("wecare", "we care"),
        "keywords": (
            "customer support", "support tickets", "support ticket management",
            "help desk", "helpdesk", "incident management", "employee support",
            "ticket management",
        ),
    },
    "Havis Xpend": {
        "url": "https://ha-shem.com/HAVIS-360/havis-xpend/",
        "domain": "ha-shem.com",
        "path_prefix": "/havis-360/havis-xpend",
        "category": "Expense Management",
        "business_problem": "Expense claims, reimbursements, and approval workflows",
        "solution_type": "Finance & Expense",
        "aliases": ("havis xpend", "xpend"),
        "keywords": (
            "expense claim", "expense claims", "expense management",
            "reimbursement", "reimbursements", "travel expenses",
            "expense approvals", "expense report", "expense reports",
        ),
    },
    "Havis Vacay": {
        "url": "https://ha-shem.com/HAVIS-360/havis-vacay/",
        "domain": "ha-shem.com",
        "path_prefix": "/havis-360/havis-vacay",
        "category": "Leave Management",
        "business_problem": "Leave management, vacation, and absence tracking",
        "solution_type": "Workforce Management",
        "aliases": ("havis vacay", "vacay"),
        "keywords": (
            "leave management", "vacation", "annual leave",
            "absence management", "time off", "employee leave",
            "leave request", "manage leave", "manages leave", "leave tracking",
        ),
    },
    "Havis iReport": {
        "url": "https://ha-shem.com/HAVIS-360/havis-ireport/",
        "domain": "ha-shem.com",
        "path_prefix": "/havis-360/havis-ireport",
        "category": "Reporting",
        "business_problem": "Employee, field, and performance reporting",
        "solution_type": "Reporting & Analytics",
        "aliases": ("havis ireport", "ireport"),
        "keywords": (
            "employee reporting", "daily reports", "weekly reports",
            "monthly reports", "field reports", "performance reporting",
            "employee reports", "field reporting",
        ),
    },
    "Havis REMA": {
        "url": "https://ha-shem.com/HAVIS-360/havis-rema/",
        "domain": "ha-shem.com",
        "path_prefix": "/havis-360/havis-rema",
        "category": "Receipt & Document Management",
        "business_problem": "Receipt management, document archiving, and expense receipts",
        "solution_type": "Document Management",
        "aliases": ("havis rema", "rema"),
        "keywords": (
            "receipt management", "receipts", "paper records",
            "expense receipts", "document archive", "receipt archive",
            "paper receipts",
        ),
    },
    "Havis eCertify": {
        "url": "https://ha-shem.com/HAVIS-360/havis-ecertify/",
        "domain": "ha-shem.com",
        "path_prefix": "/havis-360/havis-ecertify",
        "category": "Learning & Certification",
        "business_problem": "Employee training, certification, and skills development",
        "solution_type": "Learning Management",
        "aliases": ("havis ecertify", "ecertify"),
        "keywords": (
            "learning management", "employee certification", "corporate training",
            "skills development", "certification program", "employee training",
            "internal certification",
        ),
    },
    "KwikAlert": {
        "url": "https://ha-shem.com/HAVIS-360/kwikalert/",
        "domain": "ha-shem.com",
        "path_prefix": "/havis-360/kwikalert",
        "category": "Emergency Communication",
        "business_problem": "Emergency notifications, mass alerts, and crisis communication",
        "solution_type": "Communication & Alerts",
        "aliases": ("kwikalert", "kwik alert"),
        "keywords": (
            "emergency notifications", "mass notifications", "broadcast messages",
            "crisis communication", "emergency alerts", "mass alerts",
            "emergency notification", "company-wide alerts",
        ),
    },
    "AppManage": {
        "url": "https://ha-shem.com/HAVIS-360/appmanage/",
        "domain": "ha-shem.com",
        "path_prefix": "/havis-360/appmanage",
        "category": "Software Licensing",
        "business_problem": "Software licensing, activation, and subscription management",
        "solution_type": "IT & License Management",
        "aliases": ("appmanage", "app manage"),
        "keywords": (
            "software licensing", "license activation", "software subscriptions",
            "license renewals", "application activation", "license management",
            "software license",
        ),
    },
    "PayCheq": {
        "url": "https://ha-shem.com/HAVIS-360/paycheq/",
        "domain": "ha-shem.com",
        "path_prefix": "/havis-360/paycheq",
        "category": "Payroll",
        "business_problem": "Payroll, salary, and tax deduction management",
        "solution_type": "Finance & Payroll",
        "aliases": ("paycheq", "pay cheq"),
        "keywords": (
            "payroll", "salary", "employee payment", "pay slips",
            "payslips", "tax deduction", "salary payment",
        ),
    },
}
