"""Registration, sign-in, refresh-session rotation, email verification and password reset.

Owns ``auth_sessions``, ``email_verification_tokens`` and ``password_reset_tokens``
(architecture.md §2.1). Mechanism: ADR-0004. Rules: `business-rules.md` §1.1 (BR-AUTH-*).
"""
