"""
Contact form handling — extracted for clarity.
Imported into catalogue/views.py.
"""
import logging
from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

ALLOWED_SUBJECTS = {
    "Vehicle Inquiry", "Test Drive Request",
    "Price Negotiation", "Documentation Query", "General Inquiry",
}


@require_http_methods(["GET", "POST"])
def contact(request):
    context = {
        "page_title": "Contact Grandpa Motors — Nairobi, Kenya",
        "meta_description": (
            "Contact Grandpa Motors in Nairobi, Kenya. "
            "Reach our team on WhatsApp or by email for vehicle inquiries, "
            "test drives, and documentation questions."
        ),
    }

    if request.method == "GET":
        # Pre-fill vehicle ref from query string (from detail page CTA)
        vehicle_ref = request.GET.get("ref", "")
        if vehicle_ref:
            context["form_data"] = {"vehicle_ref": vehicle_ref}
        return render(request, "catalogue/contact.html", context)

    # ── POST ──
    # Honeypot check
    if request.POST.get("website"):
        # Bot detected — silently succeed
        context["form_success"] = True
        return render(request, "catalogue/contact.html", context)

    name        = request.POST.get("name", "").strip()[:100]
    email       = request.POST.get("email", "").strip()[:254]
    phone       = request.POST.get("phone", "").strip()[:20]
    subject_raw = request.POST.get("subject", "").strip()
    vehicle_ref = request.POST.get("vehicle_ref", "").strip()[:50]
    message     = request.POST.get("message", "").strip()[:2000]

    # Preserve form data for re-display on error
    form_data = {
        "name": name, "email": email, "phone": phone,
        "subject": subject_raw, "vehicle_ref": vehicle_ref, "message": message,
    }
    context["form_data"] = form_data

    # ── Validation ──
    errors = []
    if not name:
        errors.append("Full name is required.")
    if not email or "@" not in email:
        errors.append("A valid email address is required.")
    if not message or len(message) < 10:
        errors.append("Please enter a message of at least 10 characters.")
    if subject_raw and subject_raw not in ALLOWED_SUBJECTS:
        subject_raw = "General Inquiry"

    if errors:
        context["form_error"] = " ".join(errors)
        return render(request, "catalogue/contact.html", context, status=422)

    subject = subject_raw or "General Inquiry"

    # ── Build email body ──
    body_lines = [
        f"New contact form submission — Grandpa Motors",
        f"{'=' * 50}",
        f"Name:           {name}",
        f"Email:          {email}",
        f"Phone:          {phone or 'Not provided'}",
        f"Subject:        {subject}",
        f"Vehicle Ref:    {vehicle_ref or 'Not specified'}",
        f"{'─' * 50}",
        f"Message:",
        message,
        f"{'─' * 50}",
        f"Submitted from: {request.META.get('HTTP_HOST', '')}",
    ]
    full_body = "\n".join(body_lines)

    # ── Send email to admin ──
    try:
        send_mail(
            subject=f"[Grandpa Motors] {subject} — {name}",
            message=full_body,
            from_email=settings.DEALERSHIP_EMAIL,
            recipient_list=[settings.DEALERSHIP_EMAIL],
            fail_silently=False,
        )
        logger.info("Contact form submitted by %s <%s>", name, email)
    except Exception as e:
        logger.error("Contact form email failed: %s", e)
        # Don't expose mail errors to the user — log and succeed silently
        # In production, queue this as a Celery task for reliability

    context["form_success"] = True
    return render(request, "catalogue/contact.html", context)