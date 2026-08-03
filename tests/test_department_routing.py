"""Pure unit tests for determine_department — mirrors test_escalation_decision.py."""

from __future__ import annotations

from src.services.escalation.department_routing import determine_department


class TestDetermineDepartment:
    def test_billing_critical_category_routes_to_finance(self):
        assert determine_department(critical_category="billing", question="I was overcharged") == "Finance"

    def test_other_critical_categories_route_to_support(self):
        assert determine_department(critical_category="security_incident", question="hacked") == "Support"

    def test_demo_keyword_routes_to_sales(self):
        assert determine_department(critical_category=None, question="Can I get a demo?") == "Sales"

    def test_training_keyword_routes_to_training(self):
        assert determine_department(critical_category=None, question="I need training on this") == "Training"

    def test_implementation_keyword_routes_to_implementation(self):
        assert (
            determine_department(critical_category=None, question="We're starting our implementation")
            == "Implementation"
        )

    def test_default_is_support(self):
        assert determine_department(critical_category=None, question="What is SPIDIFY?") == "Support"

    def test_critical_category_wins_over_keywords(self):
        assert (
            determine_department(critical_category="billing", question="I need a demo of billing")
            == "Finance"
        )
