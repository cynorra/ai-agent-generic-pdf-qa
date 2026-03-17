"""
sample_pdfs/generate_sample_pdfs.py — Generate sample business PDFs.
Run: python sample_pdfs/generate_sample_pdfs.py
Requires: pip install fpdf2
"""
from fpdf import FPDF
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def make_pdf(filename: str, title: str, sections: list[tuple[str, str]]):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, title, ln=True, align="C")
    pdf.ln(6)

    for section_title, content in sections:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 9, section_title, ln=True)
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 7, content)
        pdf.ln(4)

    out_path = os.path.join(OUTPUT_DIR, filename)
    pdf.output(out_path)
    print(f"✅ Created: {out_path}")


# ============================================================
# 1. MARIO'S PIZZA
# ============================================================
make_pdf("marios_pizza.pdf", "Mario's Pizza - Full Menu & Policies", [
    ("About Us",
     "Mario's Pizza is a family-owned pizzeria established in 1998. We offer dine-in, "
     "takeout, and delivery. Our ingredients are fresh and locally sourced."),

    ("Hours of Operation",
     "Monday - Thursday: 11:00 AM - 10:00 PM\n"
     "Friday - Saturday: 11:00 AM - 11:00 PM\n"
     "Sunday: 12:00 PM - 9:00 PM\n"
     "We are CLOSED on Christmas Day and New Year's Day.\n"
     "All other statutory holidays: 10:00 AM - 4:00 PM"),

    ("Pizza Menu",
     "SIZES: Small (10\") $12 | Medium (12\") $16 | Large (14\") $20 | XL (16\") $24\n\n"
     "CRUSTS: Regular, Thin Crust, Stuffed Crust (+$2), Gluten-Free (+$3)\n\n"
     "TOPPINGS (included): Pepperoni, Mushroom, Green Pepper, Onion, Black Olive, "
     "Tomato, Pineapple, Ham, Chicken, Bacon\n"
     "Extra toppings: +$1.50 each\n"
     "Extra cheese: +$2.00\n\n"
     "SPECIALTY PIZZAS:\n"
     "- Margherita: tomato, mozzarella, basil - $14/$18/$22/$26\n"
     "- Meat Lovers: pepperoni, bacon, sausage, ham - $15/$19/$23/$27\n"
     "- Veggie Supreme: all veggies, extra cheese - $14/$18/$22/$26\n"
     "- BBQ Chicken: chicken, bbq sauce, onion, pepper - $15/$19/$23/$27"),

    ("Starters & Sides",
     "Garlic Bread: $5.99\n"
     "Garlic Bread with Cheese: $7.99\n"
     "Caesar Salad: $9.99\n"
     "Garden Salad: $8.99\n"
     "Chicken Wings (10 pc): $14.99\n"
     "Mozzarella Sticks (6 pc): $8.99\n"
     "Loaded Fries: $7.99"),

    ("Drinks",
     "Cola (can): $2.50\n"
     "Diet Cola (can): $2.50\n"
     "Sprite (can): $2.50\n"
     "Iced Tea (can): $2.50\n"
     "Orange Juice: $3.50\n"
     "Water (bottle): $2.00\n"
     "2L Bottle (Cola/Sprite): $4.99"),

    ("Delivery Policy",
     "Delivery available within 10 km radius.\n"
     "Minimum order for delivery: $20.00\n"
     "Delivery fee: $3.99 (free over $50)\n"
     "Estimated delivery time: 35-45 minutes\n"
     "Delivery hours: Same as store hours (until 30 min before closing)\n"
     "We deliver to apartment buildings - please include unit/buzzer number."),

    ("Payment & Ordering",
     "Payment: Cash, Visa, Mastercard, Debit, Apple Pay accepted.\n"
     "Credit card minimum: $10\n"
     "Tax: 13% HST applied to all orders.\n"
     "Gratuity not included in delivery orders.\n"
     "For large group orders (over $150), call 48 hours in advance."),

    ("Popular Items & Recommendations",
     "Our most popular pizza is the Meat Lovers Large.\n"
     "Customer favourite combo: Large Pepperoni + Garlic Bread + 2L Cola.\n"
     "We have excellent vegetarian options including Veggie Supreme and Margherita.\n"
     "Gluten-free crust available on all sizes (limited daily supply)."),

    ("Loyalty Program",
     "We do NOT currently have a formal loyalty program.\n"
     "Follow us on social media for weekly specials and promotions.\n"
     "Weekly special: Buy 2 large pizzas, get free garlic bread (Tuesdays only)."),

    ("Catering",
     "Yes, we offer catering for events of 20+ people.\n"
     "Catering menu available upon request - minimum 48 hours notice.\n"
     "Contact us at catering@mariospizza.com for quotes."),
])


# ============================================================
# 2. CLEARSKIN DERMATOLOGY
# ============================================================
make_pdf("clearskin_dermatology.pdf", "ClearSkin Dermatology Clinic", [
    ("About the Clinic",
     "ClearSkin Dermatology is a full-service skin health clinic. We offer medical and "
     "cosmetic dermatology services. Our team includes Dr. Smith and Dr. Patel."),

    ("Clinic Hours",
     "Monday: 9:00 AM - 5:00 PM\n"
     "Tuesday: 9:00 AM - 6:00 PM\n"
     "Wednesday: 9:00 AM - 5:00 PM\n"
     "Thursday: 10:00 AM - 7:00 PM\n"
     "Friday: 9:00 AM - 4:00 PM\n"
     "Saturday: 10:00 AM - 2:00 PM (Dr. Patel only)\n"
     "Sunday: CLOSED\n\n"
     "We are open on most statutory holidays except Christmas, New Year's, and Easter."),

    ("Services & Pricing",
     "MEDICAL DERMATOLOGY:\n"
     "- New Patient Consultation: 45 min | $180\n"
     "- Follow-up Consultation: 20 min | $95\n"
     "- Mole Check (full body): 20 min | $120\n"
     "- Mole Removal (simple): 30 min | $250\n"
     "- Acne Treatment Consultation: 30 min | $140\n"
     "- Acne Follow-up: 20 min | $95\n"
     "- Eczema Assessment: 30 min | $140\n"
     "- Biopsy: 30 min | $280 (lab fees separate)\n\n"
     "COSMETIC DERMATOLOGY:\n"
     "- Botox Consultation: 30 min | $120 (applied to treatment)\n"
     "- Chemical Peel: 45 min | $220\n"
     "- Laser Treatment: 60 min | from $350\n"
     "- Skin Rejuvenation: 45 min | $280"),

    ("Doctors & Availability",
     "DR. SARAH SMITH (Medical Dermatology):\n"
     "Available: Monday, Wednesday, Thursday, Friday\n"
     "Specialties: Acne, Eczema, Moles, Biopsies\n\n"
     "DR. AMIR PATEL (Cosmetic & Medical Dermatology):\n"
     "Available: Tuesday, Thursday, Saturday\n"
     "Specialties: Botox, Laser, Chemical Peels, General Dermatology"),

    ("Appointment Scheduling",
     "Appointments available in these time slots:\n"
     "Morning: 9:00, 9:20, 9:40, 10:00, 10:20, 10:40, 11:00, 11:20, 11:40 AM\n"
     "Afternoon: 1:00, 1:20, 1:40, 2:00, 2:20, 2:40, 3:00, 3:20, 3:40 PM\n"
     "Evening (Thu only): 5:00, 5:20, 5:40, 6:00, 6:20, 6:40 PM\n\n"
     "All appointments are 20 minutes unless otherwise specified.\n"
     "New patient consultations and procedures are 30-60 minutes.\n"
     "Same-day appointments sometimes available - call or chat to check."),

    ("Booking & Cancellation Policy",
     "Appointments must be booked at least 2 hours in advance.\n"
     "Cancellation: At least 24 hours notice required to avoid $50 no-show fee.\n"
     "SMS and email reminders are available upon request.\n"
     "OHIP covers most medical dermatology consultations.\n"
     "Cosmetic procedures are not OHIP-covered."),

    ("Payment & Insurance",
     "Payment: Cash, all major credit cards, debit accepted.\n"
     "Most extended health plans accepted - bring your insurance card.\n"
     "Receipts provided for all services for insurance claims.\n"
     "Payment required at time of service."),
])


# ============================================================
# 3. FRESHPRESS DRY CLEANING
# ============================================================
make_pdf("freshpress_dry_cleaning.pdf", "FreshPress Dry Cleaning & Laundry", [
    ("About FreshPress",
     "FreshPress Dry Cleaning offers professional garment care since 2005. "
     "We specialize in dry cleaning, wash & press, alterations, and leather care. "
     "Free pickup and delivery available within the city."),

    ("Hours",
     "Monday - Friday: 8:00 AM - 7:00 PM\n"
     "Saturday: 9:00 AM - 5:00 PM\n"
     "Sunday: 10:00 AM - 3:00 PM\n"
     "Closed on Christmas Day and New Year's Day."),

    ("Services & Prices",
     "WASH & PRESS:\n"
     "- Dress Shirt: $4.50\n"
     "- Casual Shirt/Blouse: $4.00\n"
     "- Pants/Slacks: $6.00\n"
     "- T-Shirt: $3.50\n\n"
     "DRY CLEAN ONLY:\n"
     "- Suit (2-piece): $18.00\n"
     "- Suit (3-piece): $24.00\n"
     "- Dress: $12.00 - $18.00\n"
     "- Blazer/Jacket: $12.00\n"
     "- Skirt: $8.00\n"
     "- Tie: $4.00\n"
     "- Coat/Winter Jacket: $22.00 - $30.00\n\n"
     "SPECIALTY:\n"
     "- Wedding Dress: from $80\n"
     "- Leather Jacket: from $35\n"
     "- Comforter (Queen): $28 | (King): $34\n"
     "- Curtains (per panel): $15"),

    ("Turnaround Time",
     "REGULAR SERVICE: 3 business days (standard)\n"
     "EXPRESS SERVICE (24 hours): +$12.00 surcharge on total\n"
     "SAME-DAY SERVICE (by noon): +$20.00 surcharge (not available for dry clean)\n\n"
     "Rush orders available for weddings and special events - call in advance."),

    ("Pickup & Delivery",
     "FREE PICKUP AND DELIVERY available!\n\n"
     "PICKUP WINDOWS:\n"
     "Morning: 9:00 AM - 11:00 AM\n"
     "Midday: 11:00 AM - 1:00 PM\n"
     "Afternoon: 2:00 PM - 5:00 PM\n\n"
     "Pickup available Monday through Saturday.\n"
     "Please be available during your chosen window (30 min flexibility each side).\n"
     "Minimum order for pickup service: $20.00\n"
     "Minimum order for delivery back: $20.00"),

    ("Policies",
     "All garments inspected upon arrival. Pre-existing stains or damage will be noted.\n"
     "We are not responsible for: fabric shrinkage due to manufacturer errors, "
     "color bleeding from poor dye fixation, items left over 60 days.\n"
     "Stain removal is attempted but not guaranteed.\n"
     "Lost garment liability: replacement cost up to $150 maximum.\n"
     "Please check all pockets before drop-off."),

    ("Payment",
     "Cash, credit card (Visa/MC), and e-transfer accepted.\n"
     "Payment upon pickup/delivery.\n"
     "Corporate accounts available - monthly invoicing.\n"
     "13% HST applied to all services."),

    ("Contact",
     "Phone: 226-555-0100\n"
     "Email: info@freshpressclean.com\n"
     "Address: 45 Market Street, Unit 2\n"
     "Booking: Call, email, or use our AI chat assistant."),
])

print("\n🎉 All sample PDFs generated successfully!")
print("You can find them in the sample_pdfs/ directory.")
