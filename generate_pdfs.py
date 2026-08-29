import os
from fpdf import FPDF

# Ensure the synthetic_rfps directory exists
os.makedirs("synthetic_rfps", exist_ok=True)

PROPOSALS = {
    "Apex Systems": {
        "summary": "Apex Systems understands the critical need for a robust and scalable architecture. We propose a state-of-the-art solution tailored for high availability and stringent security requirements.",
        "solution": "Our technical architecture leverages microservices and multi-region failover. The technical fit is extremely high, with modern API integrations fully supported. Scalability is achieved via auto-scaling clusters.",
        "timeline": "The delivery schedule is moderate. Phase 1 will be completed in 4 months, and Phase 2 in 8 months. Our team structure includes senior architects and dedicated security personnel.",
        "pricing": "Total Cost: $1,200,000.\nAssumptions: Enterprise licenses included. Higher price reflects the premium security controls.",
        "security": "We employ military-grade encryption, SOC 2 Type II certification, and comprehensive auditability controls. Privacy is guaranteed by design.",
        "support": "24/7 dedicated support model. We have 5 similar enterprise projects completed. Strong references available upon request."
    },
    "BrightPath Tech": {
        "summary": "BrightPath Tech offers the most cost-effective and rapid deployment solution to meet your immediate needs.",
        "solution": "We propose an off-the-shelf platform customization. Integrations are standard out-of-the-box connectors. Architecture is simple and monolithic for fast deployment.",
        "timeline": "Extremely fast timeline. Full rollout expected within 6 weeks. Team consists of offshore developers and one local project manager.",
        "pricing": "Total Cost: $350,000.\nAssumptions: Standard tier pricing. Low cost due to rapid deployment.",
        "security": "Basic SSL and standard data encryption. Compliance details are limited. We follow general best practices but lack formal certifications.",
        "support": "Email-only support with 48-hour SLA. Limited experience in this specific vertical, but eager to prove our capabilities."
    },
    "NexaWorks": {
        "summary": "NexaWorks provides a balanced and highly structured approach, focusing heavily on execution, risk management, and post-launch support.",
        "solution": "Our solution is a hybrid cloud model. It balances technical innovation with proven reliability. Integration plan is well-documented and scalable.",
        "timeline": "Implementation plan is our strongest asset. Detailed milestones week-by-week. Full deployment in 5 months. Comprehensive risk mitigation plan included. Staffing involves domain experts.",
        "pricing": "Total Cost: $750,000.\nAssumptions: Covers implementation and first-year maintenance. Pricing is transparent and predictable.",
        "security": "Standard industry compliance met (ISO 27001). Security controls are adequate and well-documented.",
        "support": "Industry-leading support model. Dedicated account manager, 1-hour critical response time. Extensive training program included."
    },
    "Orbit Digital": {
        "summary": "Orbit Digital brings 20 years of industry experience and an unmatched portfolio of successful deployments.",
        "solution": "We offer a proven legacy-compatible solution. While the integration plan is somewhat vague and relies on older SOAP APIs, the core engine is battle-tested.",
        "timeline": "Timeline is roughly 6-7 months. Milestones are high-level. Staffing includes veteran engineers with deep domain knowledge.",
        "pricing": "Total Cost: $600,000.\nAssumptions: Based on standard volume metrics. Medium pricing tier.",
        "security": "Legacy compliance standards met. Privacy controls are in place, though auditability requires manual log extraction.",
        "support": "Extremely strong references from Fortune 500 companies. Support model is robust, backed by our extensive historical experience."
    }
}

class RFP_PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 15)
        self.cell(0, 10, "Supplier RFP Response", border=0, ln=1, align="C")
        self.ln(5)

    def chapter_title(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 8, title, border=0, ln=1, align="L", fill=True)
        self.ln(2)

    def chapter_body(self, body):
        self.set_font("Helvetica", "", 11)
        self.multi_cell(0, 6, body)
        self.ln(4)

def create_pdf(supplier_name, content):
    pdf = RFP_PDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Proposal: {supplier_name}", ln=1, align="C")
    pdf.ln(10)
    
    sections = [
        ("Executive Summary", content["summary"]),
        ("Proposed Solution & Technical Fit", content["solution"]),
        ("Implementation Plan & Timeline", content["timeline"]),
        ("Commercial Value & Pricing", content["pricing"]),
        ("Security & Compliance", content["security"]),
        ("Support & Experience", content["support"])
    ]
    
    for title, body in sections:
        pdf.chapter_title(title)
        pdf.chapter_body(body)
        
    filename = f"synthetic_rfps/{supplier_name.replace(' ', '_')}_Proposal.pdf"
    pdf.output(filename)
    print(f"Generated {filename}")

if __name__ == "__main__":
    for supplier, content in PROPOSALS.items():
        create_pdf(supplier, content)
