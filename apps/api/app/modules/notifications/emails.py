"""Email rendering for notifications (BR-NOTIF-02).

One short message per type in Arabic and English. Bodies never include another user's
name, phone or message text — the email says *what happened* and links to the app, where
the details are shown to the signed-in recipient only.
"""

from __future__ import annotations

from html import escape
from typing import Final

from app.core.email import EmailMessage
from app.modules.notifications.models import NotificationType

_SUPPORTED: Final = ("ar", "en")

_TEXT: Final[dict[NotificationType, dict[str, tuple[str, str, str]]]] = {
    # type → locale → (subject, sentence, button label)
    NotificationType.JOIN_REQUEST_RECEIVED: {
        "ar": ("طلب انضمام جديد لرحلتك", "وصلك طلب انضمام جديد على إحدى رحلاتك.", "عرض الطلب"),
        "en": (
            "New seat request on your trip",
            "Someone asked to join one of your trips.",
            "View request",
        ),
    },
    NotificationType.JOIN_REQUEST_ACCEPTED: {
        "ar": (
            "تم قبول طلبك",
            "قَبِل السائق طلب انضمامك. تفاصيل الرحلة الكاملة متاحة الآن.",
            "عرض الرحلة",
        ),
        "en": (
            "Your seat was accepted",
            "The driver accepted your request. Full trip details are now available.",
            "View trip",
        ),
    },
    NotificationType.JOIN_REQUEST_REJECTED: {
        "ar": (
            "لم يُقبل طلبك هذه المرة",
            "لم يقبل السائق طلب انضمامك. ابحث عن رحلة أخرى في سكتك.",
            "ابحث عن رحلة",
        ),
        "en": (
            "Your request was not accepted",
            "The driver did not accept your request. Look for another ride your way.",
            "Find a ride",
        ),
    },
    NotificationType.JOIN_REQUEST_CANCELLED: {
        "ar": ("ألغى راكب حجزه", "ألغى راكب حجزه في إحدى رحلاتك وعاد المقعد متاحاً.", "عرض الرحلة"),
        "en": (
            "A passenger cancelled",
            "A passenger cancelled their seat on one of your trips. The seat is available again.",
            "View trip",
        ),
    },
    NotificationType.TRIP_UPDATED: {
        "ar": ("تعديل في رحلتك", "عدّل السائق تفاصيل رحلة أنت منضم إليها.", "عرض التعديل"),
        "en": (
            "Your trip was updated",
            "The driver changed the details of a trip you joined.",
            "See the change",
        ),
    },
    NotificationType.TRIP_STARTED: {
        "ar": (
            "بدأت الرحلة",
            "بدأ السائق الرحلة. تابع المحادثة لمعرفة مكان الالتقاء.",
            "فتح المحادثة",
        ),
        "en": (
            "Your trip has started",
            "The driver started the trip. Check the chat for the meeting point.",
            "Open chat",
        ),
    },
    NotificationType.TRIP_CANCELLED: {
        "ar": (
            "أُلغيت الرحلة",
            "أُلغيت رحلة كنت منضماً إليها. يمكنك البحث عن بديل الآن.",
            "ابحث عن بديل",
        ),
        "en": (
            "Trip cancelled",
            "A trip you joined was cancelled. You can look for an alternative now.",
            "Find another ride",
        ),
    },
    NotificationType.TRIP_COMPLETED: {
        "ar": (
            "اكتملت الرحلة — قيّم تجربتك",
            "وصلتم بالسلامة. قيّم رفيق الطريق خلال 14 يوماً.",
            "تقييم الرحلة",
        ),
        "en": (
            "Trip completed — rate your experience",
            "You arrived. Rate your travel companion within 14 days.",
            "Rate the trip",
        ),
    },
    NotificationType.TRIP_STARTING_SOON: {
        "ar": ("رحلتك تبدأ قريباً", "تبدأ رحلتك خلال ساعتين. تأكد من نقطة الالتقاء.", "عرض الرحلة"),
        "en": (
            "Your trip starts soon",
            "Your trip starts in about two hours. Confirm the meeting point.",
            "View trip",
        ),
    },
    NotificationType.TRIP_REMINDER: {
        "ar": (
            "تذكير: رحلتك غداً",
            "لديك رحلة غداً. أكد أنك ما زلت متاحاً أو ألغِ مبكراً.",
            "عرض الرحلة",
        ),
        "en": (
            "Reminder: your trip is tomorrow",
            "You have a trip tomorrow. Confirm you are still available or cancel early.",
            "View trip",
        ),
    },
    NotificationType.NEW_MESSAGE: {
        "ar": ("رسالة جديدة", "لديك رسالة جديدة في محادثة.", "فتح المحادثة"),
        "en": ("New message", "You have a new message in a conversation.", "Open chat"),
    },
    NotificationType.NEW_MATCHING_TRIP: {
        "ar": ("رحلة جديدة في سكتك", "نُشرت رحلة تطابق مساراً حفظته.", "عرض الرحلة"),
        "en": (
            "A new trip on your route",
            "A trip matching one of your saved routes was published.",
            "View trip",
        ),
    },
    NotificationType.VERIFICATION_STATUS_CHANGED: {
        "ar": ("تحديث على طلب التحقق", "تمت مراجعة طلب التحقق الخاص بك.", "عرض الحالة"),
        "en": (
            "Verification update",
            "Your verification application has been reviewed.",
            "View status",
        ),
    },
    NotificationType.RATING_RECEIVED: {
        "ar": ("تقييم جديد", "قيّمك رفيق طريق بعد رحلة مكتملة.", "عرض ملفك"),
        "en": (
            "New rating",
            "A travel companion rated you after a completed trip.",
            "View profile",
        ),
    },
    NotificationType.REPORT_UPDATED: {
        "ar": ("تحديث على بلاغك", "راجع فريق المجتمع بلاغك وحدّث حالته.", "عرض البلاغ"),
        "en": (
            "Update on your report",
            "The community team reviewed your report and updated its status.",
            "View report",
        ),
    },
    NotificationType.ACCOUNT_MODERATED: {
        "ar": (
            "إجراء على حسابك",
            "اتخذ فريق المجتمع إجراءً يخص حسابك. راجع التفاصيل.",
            "فتح الحساب",
        ),
        "en": (
            "Action on your account",
            "The community team took an action concerning your account.",
            "Open account",
        ),
    },
    NotificationType.ANNOUNCEMENT: {
        "ar": ("إعلان من فريق في سكتي", "نشر فريق المجتمع إعلاناً جديداً.", "قراءة الإعلان"),
        "en": (
            "Announcement from Fi Sikkati",
            "The community team published a new announcement.",
            "Read it",
        ),
    },
    NotificationType.REVIEW_REQUESTED: {
        "ar": (
            "طلب بانتظار مراجعتك",
            "في طلب جديد محتاج موافقتك. افتحه، راجع التفاصيل، وبعدين اقبل أو ارفض.",
            "راجع الطلب",
        ),
        "en": (
            "A request is waiting for you",
            "A new request needs your decision. "
            "Open it, review the details, then accept or reject.",
            "Review the request",
        ),
    },
}


def notification_text(type_: NotificationType, locale: str) -> tuple[str, str]:
    """Title and sentence for a phone alert. No names and no message text."""
    language = locale if locale in _SUPPORTED else "ar"
    subject, sentence, _label = _TEXT[type_][language]
    return subject, sentence


def notification_email(
    *, to: str, display_name: str, locale: str, type_: NotificationType, link: str
) -> EmailMessage:
    language = locale if locale in _SUPPORTED else "ar"
    subject, sentence, label = _TEXT[type_][language]
    greeting = f"أهلاً {display_name}،" if language == "ar" else f"Hello {display_name},"
    direction = "rtl" if language == "ar" else "ltr"
    html = (
        f'<!doctype html><html lang="{language}" dir="{direction}">'
        f'<body style="font-family:system-ui,sans-serif;line-height:1.6;color:#333333">'
        f'<h1 style="font-size:20px">{escape(subject)}</h1>'
        f"<p>{escape(greeting)}</p><p>{escape(sentence)}</p>"
        f'<p><a href="{escape(link, quote=True)}" style="display:inline-block;padding:12px 20px;'
        f'border-radius:999px;background:#333333;color:#ffffff;text-decoration:none">'
        f"{escape(label)}</a></p>"
        f'<p style="font-size:13px;color:#666666">{escape(link)}</p></body></html>'
    )
    text = f"{greeting}\n\n{sentence}\n{link}\n"
    return EmailMessage(to=to, subject=subject, text_body=text, html_body=html)
