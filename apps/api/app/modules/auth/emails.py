"""Arabic and English bodies for the authentication emails.

Kept as small literals rather than a template engine: there are four messages, they must be
reviewable in one screen, and no user-supplied text is interpolated except the display name,
which is escaped for the HTML part.
"""

from __future__ import annotations

from html import escape
from typing import Final

from app.core.email import EmailMessage

DEFAULT_LOCALE: Final = "ar"
_SUPPORTED: Final = ("ar", "en")


def _normalise(locale: str) -> str:
    return locale if locale in _SUPPORTED else DEFAULT_LOCALE


def _wrap_html(locale: str, title: str, paragraphs: list[str], action: tuple[str, str]) -> str:
    direction = "rtl" if locale == "ar" else "ltr"
    label, href = action
    body = "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)
    return (
        f'<!doctype html><html lang="{locale}" dir="{direction}">'
        f'<body style="font-family:system-ui,sans-serif;line-height:1.6;color:#333333">'
        f'<h1 style="font-size:20px">{title}</h1>{body}'
        f'<p><a href="{escape(href, quote=True)}" '
        f'style="display:inline-block;padding:12px 20px;border-radius:999px;'
        f'background:#333333;color:#ffffff;text-decoration:none">{label}</a></p>'
        f'<p style="font-size:13px;color:#666666">{escape(href)}</p>'
        f"</body></html>"
    )


def verification_email(*, to: str, display_name: str, locale: str, link: str) -> EmailMessage:
    """BR-AUTH-04: the link carries a single-use token valid for a limited time."""
    language = _normalise(locale)
    name = escape(display_name)
    if language == "ar":
        subject = "أكد بريدك الإلكتروني في «في سكتي»"
        paragraphs = [
            f"أهلاً {name}،",
            "اضغط على الزر لتأكيد بريدك الإلكتروني وتفعيل حسابك بالكامل.",
            "إذا لم تطلب هذا البريد يمكنك تجاهله.",
        ]
        action = ("تأكيد البريد الإلكتروني", link)
        text = (
            f"أهلاً {display_name}،\n\n"
            f"أكد بريدك الإلكتروني من خلال الرابط التالي:\n{link}\n\n"
            "إذا لم تطلب هذا البريد يمكنك تجاهله."
        )
    else:
        subject = "Confirm your Fi Sikkati email address"
        paragraphs = [
            f"Hello {name},",
            "Use the button below to confirm your email address and finish setting up your "
            "account.",
            "If you did not ask for this email you can ignore it.",
        ]
        action = ("Confirm email address", link)
        text = (
            f"Hello {display_name},\n\n"
            f"Confirm your email address using this link:\n{link}\n\n"
            "If you did not ask for this email you can ignore it."
        )
    return EmailMessage(
        to=to,
        subject=subject,
        text_body=text,
        html_body=_wrap_html(language, subject, paragraphs, action),
    )


def existing_account_email(*, to: str, display_name: str, locale: str, link: str) -> EmailMessage:
    """Sent when someone registers with an address that already has an account.

    Registration must answer identically for known and unknown addresses (BR-AUTH-03), so the
    *email* is what differs: the real owner is told their account already exists and is offered
    the sign-in page and a password reset.
    """
    language = _normalise(locale)
    name = escape(display_name)
    if language == "ar":
        subject = "لديك حساب بالفعل في «في سكتي»"
        paragraphs = [
            f"أهلاً {name}،",
            "تم إدخال هذا البريد الإلكتروني في صفحة إنشاء حساب جديد، ولديك حساب بالفعل.",
            "يمكنك تسجيل الدخول، أو إعادة تعيين كلمة المرور إذا نسيتها.",
        ]
        action = ("تسجيل الدخول", link)
        text = (
            f"أهلاً {display_name}،\n\n"
            "تم إدخال هذا البريد الإلكتروني في صفحة إنشاء حساب جديد، ولديك حساب بالفعل.\n"
            f"سجل الدخول من هنا:\n{link}"
        )
    else:
        subject = "You already have a Fi Sikkati account"
        paragraphs = [
            f"Hello {name},",
            "Someone entered this email address on the sign-up page, and an account already "
            "exists for it.",
            "You can sign in, or reset your password if you have forgotten it.",
        ]
        action = ("Sign in", link)
        text = (
            f"Hello {display_name},\n\n"
            "Someone entered this email address on the sign-up page, and an account already "
            f"exists for it.\nSign in here:\n{link}"
        )
    return EmailMessage(
        to=to,
        subject=subject,
        text_body=text,
        html_body=_wrap_html(language, subject, paragraphs, action),
    )


def password_reset_email(*, to: str, display_name: str, locale: str, link: str) -> EmailMessage:
    """BR-AUTH-06."""
    language = _normalise(locale)
    name = escape(display_name)
    if language == "ar":
        subject = "إعادة تعيين كلمة المرور في «في سكتي»"
        paragraphs = [
            f"أهلاً {name}،",
            "اضغط على الزر لاختيار كلمة مرور جديدة. الرابط صالح لمدة محدودة ويُستخدم مرة واحدة.",
            "إذا لم تطلب إعادة التعيين فلا داعي لأي إجراء، وكلمة مرورك الحالية لم تتغير.",
        ]
        action = ("تعيين كلمة مرور جديدة", link)
        text = (
            f"أهلاً {display_name}،\n\n"
            f"اختر كلمة مرور جديدة من خلال الرابط التالي:\n{link}\n\n"
            "إذا لم تطلب إعادة التعيين فلا داعي لأي إجراء."
        )
    else:
        subject = "Reset your Fi Sikkati password"
        paragraphs = [
            f"Hello {name},",
            "Use the button below to choose a new password. The link works once and expires "
            "shortly.",
            "If you did not ask for a reset, no action is needed and your password is unchanged.",
        ]
        action = ("Choose a new password", link)
        text = (
            f"Hello {display_name},\n\n"
            f"Choose a new password using this link:\n{link}\n\n"
            "If you did not ask for a reset, no action is needed."
        )
    return EmailMessage(
        to=to,
        subject=subject,
        text_body=text,
        html_body=_wrap_html(language, subject, paragraphs, action),
    )


def password_changed_email(*, to: str, display_name: str, locale: str, link: str) -> EmailMessage:
    """Security notice after a successful password change or reset (BR-AUTH-06, BR-AUTH-07)."""
    language = _normalise(locale)
    name = escape(display_name)
    if language == "ar":
        subject = "تم تغيير كلمة المرور"
        paragraphs = [
            f"أهلاً {name}،",
            "تم تغيير كلمة مرور حسابك وتم إنهاء الجلسات الأخرى.",
            "إذا لم تكن أنت من قام بذلك، أعد تعيين كلمة المرور فوراً وتواصل معنا.",
        ]
        action = ("فتح الحساب", link)
        text = (
            f"أهلاً {display_name}،\n\n"
            "تم تغيير كلمة مرور حسابك وتم إنهاء الجلسات الأخرى.\n"
            f"إذا لم تكن أنت، أعد تعيين كلمة المرور فوراً:\n{link}"
        )
    else:
        subject = "Your password was changed"
        paragraphs = [
            f"Hello {name},",
            "Your account password was changed and your other sessions were signed out.",
            "If this was not you, reset your password immediately and contact us.",
        ]
        action = ("Open your account", link)
        text = (
            f"Hello {display_name},\n\n"
            "Your account password was changed and your other sessions were signed out.\n"
            f"If this was not you, reset your password immediately:\n{link}"
        )
    return EmailMessage(
        to=to,
        subject=subject,
        text_body=text,
        html_body=_wrap_html(language, subject, paragraphs, action),
    )
