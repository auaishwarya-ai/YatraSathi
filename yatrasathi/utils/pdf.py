"""PDF generation (itinerary download and Karnataka brochure) with fpdf2.

fpdf2 is imported only when a PDF is requested, so the rest of the website
keeps working even if the PDF library cannot load on a computer.
"""
import io

from ..ai.responses import money, month_range

INDIGO = (55, 48, 196)
NAVY = (15, 27, 61)
GREY = (100, 116, 139)
LIGHT = (241, 243, 255)

_REPLACE = {"₹": "Rs.", "→": "->", "•": "-", "–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "✓": "-", "…": "..."}


def clean(text):
    text = str(text or "")
    for a, b in _REPLACE.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "ignore").decode("latin-1")


_PDF_CLASS = None


def _new_pdf():
    """Create the branded PDF document (imports fpdf2 on first use)."""
    global _PDF_CLASS
    if _PDF_CLASS is None:
        from fpdf import FPDF

        class BasePDF(FPDF):
            def header(self):
                self.set_fill_color(*INDIGO)
                self.rect(0, 0, 210, 22, "F")
                self.set_xy(12, 6)
                self.set_text_color(255, 255, 255)
                self.set_font("Helvetica", "B", 16)
                self.cell(0, 8, "YatraSathi")
                self.set_xy(12, 13)
                self.set_font("Helvetica", "", 9)
                self.cell(0, 5, "Your AI Travel Companion for Karnataka")
                self.set_text_color(0, 0, 0)
                self.set_y(28)

            def footer(self):
                self.set_y(-14)
                self.set_font("Helvetica", "I", 8)
                self.set_text_color(*GREY)
                self.cell(0, 6, clean(f"Costs, timings and fees are estimates - please verify before travelling.   Page {self.page_no()}"), align="C")

        _PDF_CLASS = BasePDF
    return _PDF_CLASS()


def itinerary_pdf(trip):
    """Create the itinerary PDF. Content is always rendered in English (core PDF fonts)."""
    plan = trip.plan
    if plan.get("language", "en") != "en" and plan.get("destination"):
        from ..ai.engine import get_engine
        engine = get_engine()
        if plan["destination"]["slug"] in engine.by_slug:
            plan = engine.planner.plan(plan["destination"]["slug"], plan["start_city"], plan["days"], plan["travelers"],
                                       plan.get("budget"), plan.get("interests"), plan.get("requested_style", plan["style"]),
                                       plan.get("transport", "auto"), "en")
    pdf = _new_pdf()
    pdf.set_auto_page_break(True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 10, clean(trip.title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*GREY)
    when = f" | Starts {trip.start_date.strftime('%d %b %Y')}" if trip.start_date else ""
    pdf.cell(0, 6, clean(f"{plan['start_city']} -> {plan['destination']['name']} | {plan['days']} day(s) | {plan['travelers']} traveller(s) | "
                         f"{plan['style'].title()} stay | Travel by {'cab' if plan['transport'] == 'car' else plan['transport']}{when}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    for day in plan["day_plans"]:
        pdf.set_fill_color(*LIGHT)
        pdf.set_text_color(*INDIGO)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, clean(f"  Day {day['day']}: {day['title']}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*GREY)
        pdf.cell(0, 5, clean(f"  {day['subtitle']}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Helvetica", "", 10)
        for stop in day["stops"]:
            fee = f"  (entry ~Rs.{stop['fee']}/person)" if stop.get("fee") else ""
            pdf.cell(26, 6, clean(stop.get("time") or ""), align="R")
            pdf.cell(0, 6, clean(f"   {stop['name']}{fee}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    c = plan["costs"]
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, "Estimated Cost Breakdown", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    rows = [("Transport (intercity)", c["transport"]), ("Local travel", c["local_transport"]),
            (f"Stay ({c['nights']} night(s), {c['rooms']} room(s))", c["accommodation"]), ("Food", c["food"]),
            ("Entry fees", c["entry_fees"]), ("Miscellaneous (5%)", c["misc"])]
    for label, value in rows:
        pdf.cell(120, 7, clean(label), border="B")
        pdf.cell(0, 7, clean(f"Rs. {money(value)}"), border="B", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(120, 9, "Total")
    pdf.cell(0, 9, clean(f"Rs. {money(c['total'])}  (Rs. {money(c['per_person'])} per person)"), align="R", new_x="LMARGIN", new_y="NEXT")
    if plan.get("budget"):
        pdf.set_font("Helvetica", "", 10)
        status = {"within": "Within budget", "optimized": "Optimised to fit budget", "over": "Above budget"}.get(plan["budget_status"], "")
        pdf.cell(0, 7, clean(f"Your budget: Rs. {money(plan['budget'])} - {status}"), new_x="LMARGIN", new_y="NEXT")
    if plan.get("tips"):
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Travel Tips", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, clean(plan["tips"]))
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GREY)
    pdf.multi_cell(0, 5, clean("Emergency: 112 | Police 100 | Ambulance 108 | Tourist Helpline 1363 | Women Helpline 1091"))
    return io.BytesIO(bytes(pdf.output()))


def brochure_pdf(destinations):
    pdf = _new_pdf()
    pdf.set_auto_page_break(True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 12, "Incredible Karnataka - One State. Many Worlds.", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*GREY)
    pdf.multi_cell(0, 5, clean(f"{len(destinations)} handpicked destinations across heritage sites, temples, hill stations, waterfalls, "
                               "beaches, wildlife reserves and adventure spots. Plan your trip with the YatraSathi AI Planner."))
    current = None
    for d in destinations:
        if d.category != current:
            current = d.category
            pdf.ln(3)
            pdf.set_fill_color(*INDIGO)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, clean(f"  {current}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*NAVY)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, clean(f"{d.name}  ({d.district})  -  {d.rating}/5"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(40, 40, 40)
        pdf.set_font("Helvetica", "", 9)
        fee = "Free entry" if not d.entry_fee_indian else f"Entry ~Rs.{d.entry_fee_indian}"
        pdf.multi_cell(0, 4.5, clean(f"{d.description.split('. ')[0]}. Best time: {month_range('en', d.best_from, d.best_to)}. {fee}."))
        pdf.ln(1)
    return io.BytesIO(bytes(pdf.output()))
