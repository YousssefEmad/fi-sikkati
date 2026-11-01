"""Review-outcome emails for identity and driver applications (BR-VER-03)."""

# ruff: noqa: RUF001 — Arabic copy uses alef forms Ruff treats as Latin lookalikes.

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
        f"</body></html>"
    )


def identity_decision_email(
    *, to: str, display_name: str, locale: str, approved: bool, reason: str | None, link: str
) -> EmailMessage:
    language = _normalise(locale)
    name = escape(display_name)
    if language == "ar":
        if approved:
            subject = "تم توثيق هويتك في «في سكتي»"
            paragraphs = [f"أهلاً {name}،", "راجعت الإدارة مستنداتك وتم توثيق هويتك."]
            action = ("فتح الحساب", link)
            text = f"أهلاً {display_name}،\n\nتم توثيق هويتك.\n{link}"
        else:
            subject = "لم يتم قبول مستندات الهوية"
            detail = escape(reason or "")
            paragraphs = [
                f"أهلاً {name}،",
                "لم نتمكن من قبول مستندات الهوية هذه المرة.",
                f"السبب: {detail}",
                "يمكنك رفع مستندات جديدة بعد تصحيح الملاحظات.",
            ]
            action = ("إعادة التقديم", link)
            text = (
                f"أهلاً {display_name}،\n\nلم يتم قبول مستندات الهوية.\n"
                f"السبب: {reason or ''}\n{link}"
            )
    elif approved:
        subject = "Your identity was verified"
        paragraphs = [
            f"Hello {name},",
            "An administrator reviewed your documents and verified your identity.",
        ]
        action = ("Open your account", link)
        text = f"Hello {display_name},\n\nYour identity was verified.\n{link}"
    else:
        subject = "Identity documents were not accepted"
        detail = escape(reason or "")
        paragraphs = [
            f"Hello {name},",
            "We could not accept these identity documents.",
            f"Reason: {detail}",
            "You can upload a new set after addressing the notes.",
        ]
        action = ("Submit again", link)
        text = (
            f"Hello {display_name},\n\nYour identity documents were not accepted.\n"
            f"Reason: {reason or ''}\n{link}"
        )
    return EmailMessage(
        to=to,
        subject=subject,
        text_body=text,
        html_body=_wrap_html(language, subject, paragraphs, action),
    )


def driver_decision_email(
    *, to: str, display_name: str, locale: str, approved: bool, reason: str | None, link: str
) -> EmailMessage:
    language = _normalise(locale)
    name = escape(display_name)
    if language == "ar":
        if approved:
            subject = "تمت الموافقة على حساب السائق"
            paragraphs = [
                f"أهلاً {name}،",
                "راجعت الإدارة رخصتك ومركبتك، ويمكنك الآن نشر الرحلات عندما تتوفر هذه الميزة.",
            ]
            action = ("فتح الحساب", link)
            text = f"أهلاً {display_name}،\n\nتمت الموافقة على حساب السائق.\n{link}"
        else:
            subject = "لم يتم قبول طلب السائق"
            detail = escape(reason or "")
            paragraphs = [
                f"أهلاً {name}،",
                "لم نتمكن من قبول طلب السائق هذه المرة.",
                f"السبب: {detail}",
            ]
            action = ("إعادة التقديم", link)
            text = f"أهلاً {display_name}،\n\nلم يتم قبول طلب السائق.\nالسبب: {reason or ''}\n{link}"
    elif approved:
        subject = "Your driver application was approved"
        paragraphs = [
            f"Hello {name},",
            "An administrator approved your licence and vehicle. "
            "You will be able to publish trips in a later phase.",
        ]
        action = ("Open your account", link)
        text = f"Hello {display_name},\n\nYour driver application was approved.\n{link}"
    else:
        subject = "Your driver application was not accepted"
        detail = escape(reason or "")
        paragraphs = [
            f"Hello {name},",
            "We could not approve this driver application.",
            f"Reason: {detail}",
        ]
        action = ("Apply again", link)
        text = (
            f"Hello {display_name},\n\nYour driver application was not accepted.\n"
            f"Reason: {reason or ''}\n{link}"
        )
    return EmailMessage(
        to=to,
        subject=subject,
        text_body=text,
        html_body=_wrap_html(language, subject, paragraphs, action),
    )
