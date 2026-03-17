"""
agent/business_profile.py — PDF'ten iş kurallarını otomatik çıkarır.

Her business için şunları PDF'ten öğrenir:
- Hangi yetenekler aktif? (order / appointment / info)
- Vergi oranı var mı? Varsa kaç?
- Minimum sipariş tutarı?
- Teslimat ücreti?
- Çalışma saatleri?
- Randevu süresi (varsayılan)?
- Para birimi?
- Hangi hizmet/ürün kategorileri var?
- Müşteriden hangi bilgiler gerekli?

Bu profil sistem prompt'una enjekte edilir ve tool'lara geçirilir.
Böylece kod tamamen generic kalır — tüm iş mantığı PDF'ten gelir.
"""
import json
import time
from typing import Dict, Optional, List

import structlog
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import settings
from rag.ingestion import search_knowledge
from db.client import write_audit_log, get_business_by_id, update_business

logger = structlog.get_logger("business_profile")

# --------------------------------------------------------------------------- #
#  Profile cache (business_id → profile dict)
# --------------------------------------------------------------------------- #
_profile_cache: Dict[str, Dict] = {}


PROFILE_EXTRACTION_PROMPT = """
You are analyzing a business document to extract structured configuration.
Based on the text below, extract ONLY what is explicitly stated.
If something is NOT mentioned, use null.

TEXT FROM BUSINESS PDF:
{pdf_context}

Extract the following as a valid JSON object (no markdown, no explanation, just JSON):

{{
  "business_type": "restaurant|clinic|dryclean|library|gym|salon|other",
  "capabilities": {{
    "takes_orders": true|false,
    "books_appointments": true|false,
    "provides_info_only": true|false
  }},
  "currency": "USD|EUR|GBP|CAD|TRY or null",
  "tax_rate": 0.13 (as decimal, e.g. 0.13 for 13%) or null,
  "tax_included_in_price": true|false or null,
  "minimum_order_amount": number or null,
  "delivery_fee": number or null,
  "free_delivery_above": number or null,
  "default_appointment_duration_min": number or null,
  "requires_customer_fields": ["name", "phone", "email", "address"] (only what is required),
  "requires_delivery_address": true|false,
  "has_pickup_option": true|false,
  "has_delivery_option": true|false,
  "payment_methods": ["cash", "card", "debit", "online"] or [],
  "item_categories": ["Pizza", "Drinks", "Sides"] (top-level categories from menu/services),
  "service_categories": ["Dry Clean", "Wash & Press", "Alterations"] or [],
  "hours_summary": "Mon-Fri 9-5, Sat 10-2, Sun closed" or null,
  "cancellation_policy": "24 hours notice required" or null,
  "special_rules": ["any important rule 1", "rule 2"] (max 5, only explicit rules),
  "workflow_hints": {{
    "order_confirmation_required": true|false,
    "appointment_confirmation_required": true|false,
    "collect_name_before_confirm": true|false,
    "collect_phone_before_confirm": true|false,
    "collect_address_for_delivery": true|false
  }}
}}

Return ONLY the JSON. No text before or after.
"""


def extract_business_profile(business_id: str, business_name: str) -> Dict:
    """
    PDF'ten iş kurallarını Gemini ile çıkarır.
    Sonucu hem cache'e hem Supabase'e kaydeder.
    """
    t0 = time.time()
    logger.info("profile.extraction_start", business_id=business_id, name=business_name)

    # Geniş PDF taraması — birden fazla arama
    queries = [
        "tax rate pricing delivery fee minimum order payment",
        "hours schedule appointment duration booking rules",
        "services menu items categories products",
        "cancellation policy customer information required",
        "pickup delivery address phone name required",
    ]

    all_chunks = []
    for q in queries:
        chunks = search_knowledge(query=q, business_id=business_id, k=4, session_id=None)
        all_chunks.extend(chunks)

    # Tekrar eden chunk'ları kaldır (content'e göre)
    seen = set()
    unique_chunks = []
    for c in all_chunks:
        key = c["content"][:100]
        if key not in seen:
            seen.add(key)
            unique_chunks.append(c)

    pdf_context = "\n\n---\n\n".join(c["content"] for c in unique_chunks[:15])

    logger.info("profile.chunks_collected", count=len(unique_chunks), business=business_name)

    # Gemini ile profil çıkar
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.0,  # profil çıkarımı için deterministik
        convert_system_message_to_human=True,
    )

    prompt = PROFILE_EXTRACTION_PROMPT.format(pdf_context=pdf_context[:6000])

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        # JSON temizle
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        profile = json.loads(raw)
        profile["business_id"] = business_id
        profile["business_name"] = business_name
        profile["extracted_at"] = time.time()

        logger.info(
            "profile.extraction_success",
            business=business_name,
            type=profile.get("business_type"),
            capabilities=profile.get("capabilities"),
            tax_rate=profile.get("tax_rate"),
            duration_ms=int((time.time() - t0) * 1000),
        )

    except Exception as e:
        logger.error("profile.extraction_failed", error=str(e), business=business_name)
        # Fallback: minimal generic profile
        profile = _default_profile(business_id, business_name)

    # Cache'e kaydet
    _profile_cache[business_id] = profile

    # Local DB update (businesses table description)
    try:
        update_business(
            business_id,
            description=json.dumps(profile),
            type=profile.get("business_type", "other")
        )
    except Exception as e:
        logger.warning("profile.save_failed", error=str(e))

    write_audit_log(
        event_type="profile_extraction",
        business_id=business_id,
        input_data={"chunks_used": len(unique_chunks)},
        output_data=profile,
        duration_ms=int((time.time() - t0) * 1000),
    )

    return profile


def get_business_profile(business_id: str, business_name: str = "") -> Dict:
    """
    Cache'den profil getirir. Yoksa Supabase'e bakar. Yoksa çıkarır.
    """
    if business_id in _profile_cache:
        return _profile_cache[business_id]

    # Local DB load
    try:
        biz = get_business_by_id(business_id)
        if biz and biz.get("description"):
            desc = biz["description"]
            if isinstance(desc, dict):
                profile = desc
            else:
                profile = json.loads(desc)
            
            if "business_id" in profile:
                _profile_cache[business_id] = profile
                logger.info("profile.loaded_from_db", business_id=business_id)
                return profile
    except Exception as e:
        logger.warning("profile.db_load_failed", error=str(e))

    # Yoksa yeniden çıkar
    name = business_name or business_id
    return extract_business_profile(business_id, name)


def clear_profile_cache(business_id: str = None):
    if business_id:
        _profile_cache.pop(business_id, None)
    else:
        _profile_cache.clear()


def _default_profile(business_id: str, business_name: str) -> Dict:
    """PDF'ten çıkarma başarısız olursa kullanılan minimal profil."""
    return {
        "business_id": business_id,
        "business_name": business_name,
        "business_type": "other",
        "capabilities": {
            "takes_orders": True,
            "books_appointments": True,
            "provides_info_only": True,
        },
        "currency": None,
        "tax_rate": None,
        "tax_included_in_price": None,
        "minimum_order_amount": None,
        "delivery_fee": None,
        "free_delivery_above": None,
        "default_appointment_duration_min": 30,
        "requires_customer_fields": ["name"],
        "requires_delivery_address": False,
        "has_pickup_option": True,
        "has_delivery_option": False,
        "payment_methods": [],
        "item_categories": [],
        "service_categories": [],
        "hours_summary": None,
        "cancellation_policy": None,
        "special_rules": [],
        "workflow_hints": {
            "order_confirmation_required": True,
            "appointment_confirmation_required": True,
            "collect_name_before_confirm": True,
            "collect_phone_before_confirm": False,
            "collect_address_for_delivery": True,
        },
        "extracted_at": time.time(),
        "_fallback": True,
    }


# --------------------------------------------------------------------------- #
#  Profile → Human readable summary (system prompt'a girer)
# --------------------------------------------------------------------------- #
def profile_to_system_rules(profile: Dict) -> str:
    """
    Profili sistem prompt'una eklenecek kurallara dönüştürür.
    Tüm iş mantığı burada — hiçbir şey kodda hardcode değil.
    """
    lines = []

    # Yetenekler
    caps = profile.get("capabilities", {})
    active = []
    if caps.get("takes_orders"):       active.append("ORDER TAKING")
    if caps.get("books_appointments"): active.append("APPOINTMENT SCHEDULING")
    if caps.get("provides_info_only"): active.append("INFORMATION Q&A")
    if active:
        lines.append(f"ACTIVE CAPABILITIES FOR THIS BUSINESS: {', '.join(active)}")

    # Para birimi ve vergi
    currency = profile.get("currency")
    tax_rate = profile.get("tax_rate")
    tax_included = profile.get("tax_included_in_price")

    if currency:
        lines.append(f"CURRENCY: Always show prices in {currency}")
    if tax_rate is not None:
        pct = round(tax_rate * 100, 1)
        if tax_included:
            lines.append(f"TAX: {pct}% tax is ALREADY INCLUDED in all prices. Do NOT add tax separately.")
        else:
            lines.append(f"TAX: Add {pct}% tax on top of subtotal when showing totals.")
    else:
        lines.append("TAX: No tax information found in PDF. Do NOT add any tax — show subtotal as total.")

    # Sipariş kuralları
    min_order = profile.get("minimum_order_amount")
    delivery_fee = profile.get("delivery_fee")
    free_above = profile.get("free_delivery_above")

    if min_order:
        lines.append(f"MINIMUM ORDER: {min_order} {currency or ''}. Warn customer if order is below this.")
    if delivery_fee is not None:
        lines.append(f"DELIVERY FEE: {delivery_fee} {currency or ''}")
    if free_above:
        lines.append(f"FREE DELIVERY: Orders above {free_above} {currency or ''} get free delivery.")

    # Teslimat seçenekleri
    if profile.get("has_delivery_option") and profile.get("has_pickup_option"):
        lines.append("FULFILLMENT: Ask customer if they want DELIVERY or PICKUP.")
    elif profile.get("has_delivery_option"):
        lines.append("FULFILLMENT: This business offers DELIVERY only.")
    elif profile.get("has_pickup_option"):
        lines.append("FULFILLMENT: This business offers PICKUP only (no delivery).")

    # Müşteri bilgi gereksinimleri
    required_fields = profile.get("requires_customer_fields", [])
    if required_fields:
        lines.append(f"REQUIRED CUSTOMER INFO: Always collect: {', '.join(required_fields)} before confirming.")

    if profile.get("requires_delivery_address"):
        lines.append("DELIVERY ADDRESS: Must collect full address for delivery orders.")

    # Randevu süresi
    appt_dur = profile.get("default_appointment_duration_min")
    if appt_dur:
        lines.append(f"DEFAULT APPOINTMENT DURATION: {appt_dur} minutes (unless service specifies otherwise).")

    # Ödeme yöntemleri
    payments = profile.get("payment_methods", [])
    if payments:
        lines.append(f"PAYMENT METHODS: {', '.join(payments)}")

    # Saat bilgisi
    hours = profile.get("hours_summary")
    if hours:
        lines.append(f"BUSINESS HOURS: {hours}")

    # İptal politikası
    cancel_policy = profile.get("cancellation_policy")
    if cancel_policy:
        lines.append(f"CANCELLATION POLICY: {cancel_policy}")

    # Özel kurallar
    special_rules = profile.get("special_rules", [])
    if special_rules:
        lines.append("SPECIAL RULES:")
        for rule in special_rules:
            lines.append(f"  - {rule}")

    # Workflow ipuçları
    hints = profile.get("workflow_hints", {})
    if hints.get("order_confirmation_required"):
        lines.append("WORKFLOW: Always show full order summary and ask for confirmation before calling confirm_order.")
    if hints.get("appointment_confirmation_required"):
        lines.append("WORKFLOW: Always confirm appointment details with customer before calling book_appointment.")

    return "\n".join(lines)
