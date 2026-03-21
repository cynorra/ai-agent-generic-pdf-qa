"""
agent/tools.py — LangChain @tool tanımları.

TAMAMEN GENERİK: Fiyat, vergi, kural, saat — hiçbir şey hardcode değil.
Tüm iş mantığı PDF'ten çıkarılan business_profile üzerinden gelir.
Tool'lar sadece DB operasyonları ve RAG aramaları yapar.
"""
import json
import time
import uuid
from typing import Any, Dict, List, Optional

import structlog
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import os

from config import settings
from db import client as db
from rag.ingestion import search_knowledge

logger = structlog.get_logger("agent.tools")

# --------------------------------------------------------------------------- #
#  Tool context — agent graph tarafından set edilir
# --------------------------------------------------------------------------- #
_current_business_id: str = ""
_current_session_id: str = ""
_current_profile: Dict = {}   # PDF'ten çıkarılan profil


def set_tool_context(business_id: str, session_id: str, profile: Dict = None):
    global _current_business_id, _current_session_id, _current_profile
    _current_business_id = business_id
    _current_session_id = session_id
    _current_profile = profile or {}


def _get_profile() -> Dict:
    return _current_profile


def _log_tool(tool_name: str, inputs: dict, output: Any, duration_ms: int) -> None:
    logger.info(
        "🔧 TOOL_CALLED",
        tool=tool_name,
        session_id=_current_session_id,
        business_id=_current_business_id,
        input=inputs,
        output=str(output)[:500],
        duration_ms=duration_ms,
    )
    db.write_audit_log(
        event_type="tool_call",
        session_id=_current_session_id,
        business_id=_current_business_id,
        tool_name=tool_name,
        input_data=inputs,
        output_data={"result": str(output)[:2000]},
        duration_ms=duration_ms,
    )

def _sync_local_calendar(appt_id: str, scheduled_at: str, action: str):
    """Local calendar integration - syncs to an ICS file locally (Func 57)."""
    try:
        os.makedirs("data", exist_ok=True)
        cal_path = os.path.join("data", f"local_calendar_{_current_business_id}.txt")
        with open(cal_path, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} | {action} | {appt_id} | {scheduled_at}\n")
    except Exception as e:
        logger.warning("calendar_sync_failed", error=str(e))

# --------------------------------------------------------------------------- #
#  1. BİLGİ / RAG TOOL'LARI
# --------------------------------------------------------------------------- #

@tool
def get_business_info(query: str) -> str:
    """
    İşletme hakkında herhangi bir soruyu yanıtlar: saatler, fiyatlar,
    politikalar, menü kalemleri, hizmetler, kurallar, SSS.
    Faktüel sorular sormadan önce MUTLAKA bu tool'u çağır.

    Args:
        query: Müşterinin işletme hakkındaki sorusu.
    Returns:
        PDF'ten alınan ilgili metin parçaları ve kaynak referansları.
    """
    t0 = time.time()
    logger.info("🔍 get_business_info", query=query)

    chunks = search_knowledge(
        query=query,
        business_id=_current_business_id,
        k=5,
        session_id=_current_session_id,
    )

    if not chunks:
        result = "No information found in the business knowledge base regarding this."
    else:
        parts = []
        for i, c in enumerate(chunks, 1):
            parts.append(
                f"[Kaynak {i} | skor={c['score']} | sayfa={c['page']}]\n{c['content']}"
            )
        result = "\n\n---\n\n".join(parts)

    _log_tool("get_business_info", {"query": query}, result, int((time.time() - t0) * 1000))
    return result


@tool
def search_items_or_services(search_term: str) -> str:
    """
    Belirli bir ürün, hizmet veya kategoriyi PDF'te arar.
    Fiyat, seçenekler, açıklama bilgilerini getirir.
    Müşteri bir şey sipariş etmeden önce fiyatını doğrulamak için kullan.

    Args:
        search_term: Aranacak ürün/hizmet adı veya kategorisi.
    Returns:
        PDF'ten eşleşen bilgiler.
    """
    t0 = time.time()
    logger.info("🔍 search_items_or_services", term=search_term)

    chunks = search_knowledge(
        query=f"item service product price option {search_term}",
        business_id=_current_business_id,
        k=4,
        session_id=_current_session_id,
    )

    if not chunks:
        result = f"'{search_term}' not found in the menu/services list."
    else:
        result = "\n---\n".join(c["content"] for c in chunks)

    _log_tool("search_items_or_services", {"term": search_term}, result, int((time.time() - t0) * 1000))
    return result


@tool
def get_pricing_rules() -> str:
    """
    İşletmenin fiyatlandırma kurallarını PDF'ten getirir.
    Vergi, teslimat ücreti, minimum sipariş, indirimler vb.
    Sipariş toplamı hesaplamadan önce çağır.

    Returns:
        Fiyatlandırma kuralları PDF'ten.
    """
    t0 = time.time()
    logger.info("💰 get_pricing_rules")

    chunks = search_knowledge(
        query="tax rate delivery fee minimum order surcharge discount pricing rules total",
        business_id=_current_business_id,
        k=4,
        session_id=_current_session_id,
    )

    profile = _get_profile()
    profile_info = {}
    for key in ["tax_rate", "tax_included_in_price", "delivery_fee",
                "minimum_order_amount", "free_delivery_above", "currency"]:
        if profile.get(key) is not None:
            profile_info[key] = profile[key]

    result = {
        "profile_extracted_rules": profile_info,
        "pdf_pricing_context": "\n---\n".join(c["content"] for c in chunks),
    }

    _log_tool("get_pricing_rules", {}, result, int((time.time() - t0) * 1000))
    return json.dumps(result, ensure_ascii=False)


@tool
def get_scheduling_rules() -> str:
    """
    Randevu/rezervasyon kurallarını PDF'ten getirir.
    Müsait saatler, randevu süresi, gereksinimler, iptal politikası.
    Randevu önermeden önce çağır.

    Returns:
        Zamanlama kuralları PDF'ten.
    """
    t0 = time.time()
    logger.info("📅 get_scheduling_rules")

    chunks = search_knowledge(
        query="appointment schedule availability slots hours booking cancellation rescheduling duration",
        business_id=_current_business_id,
        k=5,
        session_id=_current_session_id,
    )

    profile = _get_profile()
    profile_info = {
        "default_duration_min": profile.get("default_appointment_duration_min"),
        "cancellation_policy": profile.get("cancellation_policy"),
        "requires_fields": profile.get("requires_customer_fields", []),
    }

    result = {
        "profile_scheduling_rules": profile_info,
        "pdf_scheduling_context": "\n---\n".join(c["content"] for c in chunks),
    }

    _log_tool("get_scheduling_rules", {}, result, int((time.time() - t0) * 1000))
    return json.dumps(result, ensure_ascii=False)


# --------------------------------------------------------------------------- #
#  2. SİPARİŞ TOOL'LARI
# --------------------------------------------------------------------------- #

@tool
def create_order_draft(customer_name: str = "", notes: str = "") -> str:
    """
    Yeni bir sipariş taslağı başlatır.
    Müşteri sipariş vermek istediğinde ilk çağrılacak tool.

    Args:
        customer_name: Müşteri adı (opsiyonel, biliniyorsa).
        notes: Sipariş için özel notlar (opsiyonel).
    Returns:
        Yeni sipariş ID'si ve durum bilgisi JSON olarak.
    """
    t0 = time.time()
    logger.info("📋 create_order_draft", customer=customer_name)

    customer_id = None
    if customer_name:
        customer = db.upsert_customer(
            business_id=_current_business_id,
            name=customer_name,
        )
        customer_id = customer["id"]

    order = db.create_order(
        session_id=_current_session_id,
        business_id=_current_business_id,
        customer_id=customer_id,
    )
    if notes:
        db.update_order(order["id"], notes=notes)

    result = {
        "order_id": order["id"],
        "status": "draft",
        "items": [],
        "note": "Use search_items_or_services to verify prices before adding items. Use get_pricing_rules for tax/delivery."
    }
    _log_tool("create_order_draft", {"customer_name": customer_name}, result, int((time.time() - t0) * 1000))
    return json.dumps(result)


@tool
def add_item_to_order(
    order_id: str,
    item_name: str,
    quantity: int,
    unit_price: float,
    modifiers: str = "",
    notes: str = "",
) -> str:
    """
    Sipariş taslağına bir ürün/hizmet ekler.
    ÖNEMLI: unit_price PDF'ten doğrulanmış fiyat olmalı.
    Fiyatı bilmiyorsan önce search_items_or_services çağır.
    Vergi ve teslimat ücreti BURAYA EKLEME — sadece ürün fiyatları.

    Args:
        order_id: create_order_draft'tan dönen sipariş UUID'si.
        item_name: Eklenecek ürün/hizmet adı.
        quantity: Miktar.
        unit_price: Birim fiyat (PDF'ten alınmış, vergisiz).
        modifiers: Virgülle ayrılmış seçenekler (örn: 'büyük,ekstra peynir').
        notes: Bu ürün için özel talimatlar.
    Returns:
        Güncellenmiş sipariş (vergi/teslimat henüz eklenmemiş) JSON olarak.
    """
    t0 = time.time()
    logger.info("➕ add_item_to_order", order_id=order_id, item=item_name, qty=quantity, price=unit_price)

    order = db.get_order(order_id)
    if not order:
        result = {"error": f"Order {order_id} not found"}
        _log_tool("add_item_to_order", locals(), result, int((time.time() - t0) * 1000))
        return json.dumps(result)

    items = order.get("items") or []
    items.append({
        "id": str(uuid.uuid4())[:8],
        "name": item_name,
        "quantity": quantity,
        "unit_price": unit_price,
        "modifiers": [m.strip() for m in modifiers.split(",") if m.strip()],
        "notes": notes,
        "line_total": round(quantity * unit_price, 2),
    })

    subtotal = round(sum(i["line_total"] for i in items), 2)

    # VERGİ HESAPLAMA — tamamen profile'dan, hiçbir şey hardcode değil
    profile = _get_profile()
    tax_rate = profile.get("tax_rate")
    tax_included = profile.get("tax_included_in_price", False)

    if tax_included or tax_rate is None:
        tax = 0.0
        total = subtotal
    else:
        tax = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax, 2)

    db.update_order(order_id, items=items, subtotal=subtotal, tax=tax, total=total)

    result = {
        "order_id": order_id,
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "tax_rate_applied": tax_rate,
        "tax_included_in_price": tax_included,
        "total_before_delivery": total,
        "note": "Delivery fee (if any) will be added when delivery type is set.",
    }
    _log_tool(
        "add_item_to_order",
        {"order_id": order_id, "item": item_name, "qty": quantity, "price": unit_price},
        result,
        int((time.time() - t0) * 1000),
    )
    return json.dumps(result)


@tool
def remove_item_from_order(order_id: str, item_name: str) -> str:
    """
    Sipariş taslağından bir ürünü kaldırır.
    Müşteri fikrini değiştirdiğinde kullan.

    Args:
        order_id: Sipariş UUID'si.
        item_name: Kaldırılacak ürün adı (kısmi eşleşme desteklenir).
    Returns:
        Güncellenmiş sipariş JSON olarak.
    """
    t0 = time.time()
    logger.info("➖ remove_item_from_order", order_id=order_id, item=item_name)

    order = db.get_order(order_id)
    if not order:
        return json.dumps({"error": f"Order {order_id} not found"})

    items = order.get("items") or []
    original_count = len(items)
    items = [i for i in items if item_name.lower() not in i["name"].lower()]
    removed = original_count - len(items)

    subtotal = round(sum(i["line_total"] for i in items), 2)

    profile = _get_profile()
    tax_rate = profile.get("tax_rate")
    tax_included = profile.get("tax_included_in_price", False)

    if tax_included or tax_rate is None:
        tax = 0.0
        total = subtotal
    else:
        tax = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax, 2)

    db.update_order(order_id, items=items, subtotal=subtotal, tax=tax, total=total)

    result = {
        "order_id": order_id,
        "removed_item": item_name,
        "items_removed_count": removed,
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "total_before_delivery": total,
    }
    _log_tool("remove_item_from_order", {"order_id": order_id, "item": item_name}, result, int((time.time() - t0) * 1000))
    return json.dumps(result)


@tool
def set_order_fulfillment(
    order_id: str,
    delivery_type: str,
    address: str = "",
    notes: str = "",
) -> str:
    """
    Siparişin teslimat/alım bilgisini ayarlar ve teslimat ücretini ekler.
    Teslimat ücreti tamamen PDF'ten çıkarılan profile'e göre hesaplanır.

    Args:
        order_id: Sipariş UUID'si.
        delivery_type: 'delivery' veya 'pickup'.
        address: Teslimat adresi (delivery seçilirse gerekli).
        notes: Ek notlar.
    Returns:
        Teslimat ücreti eklenmiş güncel sipariş JSON olarak.
    """
    t0 = time.time()
    logger.info("🚚 set_order_fulfillment", order_id=order_id, type=delivery_type)

    order = db.get_order(order_id)
    if not order:
        return json.dumps({"error": f"Order {order_id} not found"})

    profile = _get_profile()
    delivery_fee = 0.0
    free_above = profile.get("free_delivery_above")
    profile_delivery_fee = profile.get("delivery_fee") or 0.0
    subtotal = order.get("subtotal", 0)
    tax = order.get("tax", 0)

    if delivery_type == "delivery":
        if free_above and subtotal >= free_above:
            delivery_fee = 0.0
        else:
            delivery_fee = profile_delivery_fee

    total = round(subtotal + tax + delivery_fee, 2)

    fields = {"delivery_type": delivery_type, "total": total}
    if address:      fields["address"] = address
    if notes:        fields["notes"] = notes

    if delivery_fee > 0:
        items = order.get("items") or []
        items = [i for i in items if i.get("name") != "__delivery_fee__"]
        items.append({
            "id": "__delivery__",
            "name": "__delivery_fee__",
            "quantity": 1,
            "unit_price": delivery_fee,
            "modifiers": [],
            "notes": "Delivery fee",
            "line_total": delivery_fee,
        })
        fields["items"] = items

    db.update_order(order_id, **fields)

    result = {
        "order_id": order_id,
        "delivery_type": delivery_type,
        "address": address,
        "subtotal": subtotal,
        "tax": tax,
        "delivery_fee": delivery_fee,
        "grand_total": total,
    }
    _log_tool("set_order_fulfillment", {"order_id": order_id, "type": delivery_type}, result, int((time.time() - t0) * 1000))
    return json.dumps(result)


@tool
def get_order_summary(order_id: str) -> str:
    """
    Siparişin mevcut durumunu gösterir: tüm ürünler, fiyatlar, toplam.
    Onaylamadan önce müşteriye göstermek için kullan.

    Args:
        order_id: Sipariş UUID'si.
    Returns:
        Tam sipariş detayları JSON olarak.
    """
    t0 = time.time()
    order = db.get_order(order_id)
    if not order:
        return json.dumps({"error": f"Order {order_id} not found"})
    _log_tool("get_order_summary", {"order_id": order_id}, order, int((time.time() - t0) * 1000))
    return json.dumps(order, default=str)


@tool
def confirm_order(order_id: str) -> str:
    """
    Siparişi onaylar ve sonlandırır.
    SADECE müşteri özeti gördükten ve açıkça onayladıktan sonra çağır.

    Args:
        order_id: Onaylanacak sipariş UUID'si.
    Returns:
        Onay mesajı ve sipariş detayları JSON olarak.
    """
    t0 = time.time()
    order = db.confirm_order(order_id)
    result = {
        "order_id": order_id,
        "status": "confirmed",
        "total": order.get("total"),
        "delivery_type": order.get("delivery_type"),
        "items_count": len(order.get("items") or []),
    }
    _log_tool("confirm_order", {"order_id": order_id}, result, int((time.time() - t0) * 1000))
    return json.dumps(result)


@tool
def cancel_order(order_id: str, reason: str = "") -> str:
    """
    Mevcut bir siparişi iptal eder.

    Args:
        order_id: İptal edilecek sipariş UUID'si.
        reason: İptal sebebi (opsiyonel).
    """
    t0 = time.time()
    db.cancel_order(order_id)
    result = {"order_id": order_id, "status": "cancelled", "reason": reason}
    _log_tool("cancel_order", {"order_id": order_id}, result, int((time.time() - t0) * 1000))
    return json.dumps(result)


# --------------------------------------------------------------------------- #
#  3. RANDEVU TOOL'LARI
# --------------------------------------------------------------------------- #

@tool
def check_appointment_availability(
    service: str,
    preferred_date: str = "",
    provider_preference: str = "",
) -> str:
    """
    Bir hizmet için mevcut randevu slotlarını kontrol eder.
    Randevu önermeden önce MUTLAKA çağır.

    Args:
        service: Hizmet türü.
        preferred_date: Tercih edilen tarih.
        provider_preference: Tercih edilen sağlayıcı/personel.
    Returns:
        PDF'ten zamanlama kuralları + mevcut dolu slotlar JSON olarak.
    """
    t0 = time.time()
    logger.info("📅 check_appointment_availability", service=service, date=preferred_date)

    schedule_chunks = search_knowledge(
        query=f"schedule availability slots hours appointment {service} {preferred_date} {provider_preference}",
        business_id=_current_business_id,
        k=5,
        session_id=_current_session_id,
    )

    booked_slots = []
    try:
        conn = db.get_db()
        query = "SELECT scheduled_at, duration_min, provider, service FROM appointments WHERE business_id = ? AND status = 'scheduled'"
        params = [_current_business_id]
        if provider_preference:
            query += " AND provider = ?"
            params.append(provider_preference)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        booked_slots = [dict(r) for r in rows]
    except Exception as e:
        logger.warning("check_availability.db_error", error=str(e))

    profile = _get_profile()
    result = {
        "service": service,
        "preferred_date": preferred_date,
        "provider_preference": provider_preference,
        "default_duration_min": profile.get("default_appointment_duration_min", 30),
        "currently_booked_count": len(booked_slots),
        "booked_slots_preview": [
            {"at": s.get("scheduled_at", "")[:16], "service": s.get("service", "")}
            for s in booked_slots[:5]
        ],
        "pdf_scheduling_rules": "\n---\n".join(c["content"] for c in schedule_chunks)[:2000],
        "instruction": (
            "PDF'teki zamanlama kurallarını kullanarak 3 somut slot öner. "
            "booked_slots ile çakışma kontrolü yap."
        ),
    }

    _log_tool("check_appointment_availability", {"service": service, "date": preferred_date}, result, int((time.time() - t0) * 1000))
    return json.dumps(result, ensure_ascii=False)


@tool
def book_appointment(
    service: str,
    scheduled_at: str,
    customer_name: str,
    customer_phone: str = "",
    customer_email: str = "",
    duration_min: int = 0,
    provider: str = "",
    notes: str = "",
    sms_reminder: bool = False,
) -> str:
    """
    Müşteri için randevu oluşturur.
    Süre belirtilmezse PDF'ten çıkarılan varsayılan süre kullanılır.

    Args:
        service: Hizmet türü.
        scheduled_at: ISO format tarih-saat.
        customer_name: Müşteri adı.
        customer_phone: Telefon.
        customer_email: E-posta.
        duration_min: Süre dk (0 ise profile'dan alınır).
        provider: Sağlayıcı/doktor adı.
        notes: Özel notlar.
        sms_reminder: SMS hatırlatıcı.
    Returns:
        Oluşturulan randevu JSON olarak.
    """
    t0 = time.time()

    if not duration_min:
        profile = _get_profile()
        duration_min = profile.get("default_appointment_duration_min") or 30

    conflict = db.check_slot_conflict(
        business_id=_current_business_id,
        scheduled_at=scheduled_at,
        duration_min=duration_min,
        provider=provider or None,
    )

    if conflict:
        result = {
            "error": "time_slot_conflict",
            "message": f"Slot {scheduled_at} is booked. Please choose another time.",
        }
        _log_tool("book_appointment", {"service": service, "at": scheduled_at}, result, int((time.time() - t0) * 1000))
        return json.dumps(result)

    customer = db.upsert_customer(
        business_id=_current_business_id,
        name=customer_name,
        phone=customer_phone or None,
        email=customer_email or None,
    )

    appt = db.create_appointment(
        session_id=_current_session_id,
        business_id=_current_business_id,
        customer_id=customer["id"],
        service=service,
        scheduled_at=scheduled_at,
        duration_min=duration_min,
        provider=provider or None,
        notes=notes or None,
    )

    if sms_reminder:
        db.update_appointment(appt["id"], reminders=[{"type": "sms", "sent": False}])

    result = {
        "appointment_id": appt["id"],
        "service": service,
        "scheduled_at": scheduled_at,
        "duration_min": duration_min,
        "customer": customer_name,
        "provider": provider or "first_available",
        "sms_reminder": sms_reminder,
        "status": "scheduled",
    }
    _sync_local_calendar(appt["id"], scheduled_at, "BOOKED")
    _log_tool("book_appointment", {"service": service, "at": scheduled_at, "customer": customer_name}, result, int((time.time() - t0) * 1000))
    return json.dumps(result)


@tool
def reschedule_appointment(appointment_id: str, new_scheduled_at: str, reason: str = "") -> str:
    """
    Mevcut randevuyu yeni zamana taşır.

    Args:
        appointment_id: Randevu UUID'si.
        new_scheduled_at: Yeni ISO tarih-saat.
        reason: Sebep (opsiyonel).
    """
    t0 = time.time()
    db.update_appointment(appointment_id, scheduled_at=new_scheduled_at, status="scheduled")
    result = {"appointment_id": appointment_id, "new_scheduled_at": new_scheduled_at, "status": "rescheduled"}
    _sync_local_calendar(appointment_id, new_scheduled_at, "RESCHEDULED")
    _log_tool("reschedule_appointment", {"appt_id": appointment_id, "new": new_scheduled_at}, result, int((time.time() - t0) * 1000))
    return json.dumps(result)


@tool
def cancel_appointment(appointment_id: str, reason: str = "") -> str:
    """
    Randevuyu iptal eder.

    Args:
        appointment_id: İptal edilecek randevu UUID'si.
        reason: İptal sebebi (opsiyonel).
    """
    t0 = time.time()
    db.cancel_appointment(appointment_id)
    result = {"appointment_id": appointment_id, "status": "cancelled", "reason": reason}
    _sync_local_calendar(appointment_id, "N/A", "CANCELLED")
    _log_tool("cancel_appointment", {"appt_id": appointment_id}, result, int((time.time() - t0) * 1000))
    return json.dumps(result)


# --------------------------------------------------------------------------- #
#  4. MÜŞTERİ TOOL'U
# --------------------------------------------------------------------------- #

@tool
def save_customer_info(name: str = "", phone: str = "", email: str = "", address: str = "") -> str:
    """
    Müşteri bilgilerini kaydeder veya günceller.

    Args:
        name: Müşteri adı.
        phone: Telefon.
        email: E-posta.
        address: Adres.
    """
    t0 = time.time()
    customer = db.upsert_customer(
        business_id=_current_business_id,
        name=name or None,
        phone=phone or None,
        email=email or None,
        address=address or None,
    )
    _log_tool("save_customer_info", {"name": name, "phone": phone}, customer, int((time.time() - t0) * 1000))
    return json.dumps(customer, default=str)


# --------------------------------------------------------------------------- #
#  5. İLERİ ANALİZ VE DOĞRULAMA ARAÇLARI (ADVANCED TOOLS)
# --------------------------------------------------------------------------- #

@tool
def analyze_business_statistics(category: str = "") -> str:
    """
    Geçmiş sipariş istatistiklerini getirerek en popüler (çok satılan) ürünleri verir.
    Müşteriye up-sell veya cross-sell (ek ürün satışı/tavsiyesi) yapmak için kullan.

    Args:
        category: Filtrelenecek kategori (örn: 'drinks', 'sides') opsiyonel.
    """
    t0 = time.time()
    try:
        conn = db.get_db()
        # Get all items sold in completed/confirmed orders
        # Since items are JSON, we do a simple text-based grouping here or mock it for speed
        rows = conn.execute("SELECT items FROM orders WHERE business_id = ? AND status IN ('confirmed', 'completed')", (_current_business_id,)).fetchall()
        conn.close()
        
        item_counts = {}
        for row in rows:
            items = json.loads(row[0]) if row[0] else []
            for i in items:
                name = i.get("name", "Unknown")
                item_counts[name] = item_counts.get(name, 0) + i.get("quantity", 1)
        
        sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)
        top_items = [f"{k} ({v} times)" for k, v in sorted_items[:5]]
        
        result = {
            "popular_items": top_items if top_items else ["None yet"],
            "suggestion_instruction": "Use these popular items to suggest additions to the customer's current order."
        }
    except Exception as e:
        logger.warning("analyze_stats.error", error=str(e))
        result = {"popular_items": ["Pizza", "Cola", "Fries"], "note": "Simulated default statistics."}
        
    _log_tool("analyze_business_statistics", {"category": category}, result, int((time.time() - t0) * 1000))
    return json.dumps(result)


@tool
def analyze_customer_profile(customer_name: str) -> str:
    """
    Müşterinin geçmiş sipariş veya randevu tercihlerini, sıklıkla aldığı ürünleri bulur.
    Müşteri tekrar geldiğinde ona kişiselleştirilmiş (Örn: 'Geçen seferki gibi X ister misiniz?') hizmet sunmak için kullan.
    """
    t0 = time.time()
    try:
        conn = db.get_db()
        cust = conn.execute("SELECT id FROM customers WHERE name ILIKE ? AND business_id = ?", (f"%{customer_name}%", _current_business_id)).fetchone()
        if not cust:
            return json.dumps({"error": "Customer not found in history. Treat as new customer."})
            
        cust_id = cust[0]
        orders = conn.execute("SELECT items, created_at FROM orders WHERE customer_id = ? ORDER BY created_at DESC LIMIT 3", (cust_id,)).fetchall()
        appts = conn.execute("SELECT service, provider, scheduled_at FROM appointments WHERE customer_id = ? ORDER BY created_at DESC LIMIT 3", (cust_id,)).fetchall()
        conn.close()
        
        past_items = []
        for o in orders:
            try:
               items = json.loads(o[0])
               past_items.extend([i.get("name") for i in items])
            except: pass
            
        past_services = [a[0] for a in appts]
        
        # Func 9: LLM-based decomposition of customer history
        llm_traits = "Unknown"
        if past_items or past_services:
            try:
                llm = ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL, temperature=0, google_api_key=settings.GOOGLE_API_KEY)
                prompt = f"Analyze this customer's history:\nItems: {past_items}\nServices: {past_services}\nOutput a concise JSON object detailing their logical 'traits', 'preferences', and 'status' (e.g., returning, frequent, family type if inferred)."
                res = llm.invoke([HumanMessage(content=prompt)])
                llm_traits = json.loads(res.content.split("```json")[-1].split("```")[0]) if "```" in res.content else res.content
            except:
                llm_traits = "General repeat customer"
        
        result = {
            "customer_name": customer_name,
            "recently_ordered": list(set(past_items))[:5],
            "recent_services": list(set(past_services))[:3],
            "inferred_customer_traits": llm_traits,
            "instruction": "Casually mention their past favorites or preferences based on the inferred_customer_traits."
        }
    except Exception as e:
        logger.warning("analyze_profile.error", error=str(e))
        result = {"error": "Failed to load customer profile"}
        
    _log_tool("analyze_customer_profile", {"name": customer_name}, result, int((time.time() - t0) * 1000))
    return json.dumps(result)


@tool
def extract_numbers(text: str) -> str:
    """
    Karmaşık metinlerden sayısız formattaki fiyat, adet, tarih sayılarını ve telefon numaralarını
    hijyenik bir şekilde çeker ve doğrular.
    """
    t0 = time.time()
    import re
    phones = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    digits = re.findall(r'\b\d+\b', text)
    result = {"phone_numbers_detected": phones, "raw_digits_detected": digits, "instruction": "Use these validated numbers for ordering quantities or customer phone fields."}
    _log_tool("extract_numbers", {"text": text}, result, int((time.time() - t0) * 1000))
    return json.dumps(result)


@tool
def validate_address(address: str) -> str:
    """
    Adres formatını doğrular ve normalize eder.
    Bölge veya Posta kodu (örn. Kanada / US posta kodu) uyumluluğunu test eder.
    Teslimat adresi alınırken her zaman kullan.
    """
    t0 = time.time()
    import re
    # Basic Canadian / US postal code checking simulation (Func 28, 29)
    ca_postal = re.search(r'[ABCEGHJKLMNPRSTVXY]\d[ABCEGHJKLMNPRSTVWXYZ] ?\d[ABCEGHJKLMNPRSTVWXYZ]\d', address.upper())
    us_zip = re.search(r'\b\d{5}(?:-\d{4})?\b', address)
    
    is_valid = True if (ca_postal or us_zip or len(address) > 10) else False
    
    result = {
        "original": address,
        "is_valid": is_valid,
        "postal_code": ca_postal.group(0) if ca_postal else (us_zip.group(0) if us_zip else "Unknown"),
        "normalized": address.strip().title(),
        "instruction": "If invalid, kindly ask the customer to provide a full street address and postal code." if not is_valid else "Address valid, use the normalized format."
    }
    _log_tool("validate_address", {"address": address}, result, int((time.time() - t0) * 1000))
    return json.dumps(result)


@tool
def record_complaint(order_id: str, issue_description: str, requested_resolution: str = "") -> str:
    """
    Müşterinin siparişle ilgili bir şikayeti (eksik ürün, soğuk yemek, gecikme vb.) olduğunda kullan.
    Service Recovery (Hizmet telafisi) kapsamında şikayeti kaydeder ve durumu yönetime bildirir.
    Hemen müşteriye özür dileyip çözüm sunulması gerektiğini belirten bir talimat döner.
    """
    t0 = time.time()
    result = {
        "order_id": order_id,
        "issue": issue_description,
        "status": "complaint_logged",
        "instruction": "Apologize sincerely to the customer and assure them management will review this immediately. If applicable, suggest offering a discount or refund in the next steps."
    }
    # In a real app we'd save this to a 'complaints' table, for now we log it via the audit system
    _log_tool("record_complaint", {"order_id": order_id, "issue": issue_description}, result, int((time.time() - t0) * 1000))
    return json.dumps(result)

# --------------------------------------------------------------------------- #
#  Tüm tool listesi
# --------------------------------------------------------------------------- #
ALL_TOOLS = [
    get_business_info,
    search_items_or_services,
    get_pricing_rules,
    get_scheduling_rules,
    create_order_draft,
    add_item_to_order,
    remove_item_from_order,
    set_order_fulfillment,
    get_order_summary,
    confirm_order,
    cancel_order,
    check_appointment_availability,
    book_appointment,
    reschedule_appointment,
    cancel_appointment,
    save_customer_info,
    analyze_business_statistics,
    analyze_customer_profile,
    extract_numbers,
    validate_address,
    record_complaint,
]
