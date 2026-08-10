"""Self-service organization signup and team invitations (Phase 28).

Deliberately a separate package from ``src/services/admin/`` — everything
in ``admin/`` is reached exclusively through ``require_super_admin``-gated
routes today, while this package is public-facing (org signup) or
workspace-admin-facing (invitations), never platform-admin-only.
"""
