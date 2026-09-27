import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfgen import canvas

PDF_PATH = Path.home() / "quant_pipeline" / "research" / "HL3A_Quantitative_Research_Dossier.pdf"

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            if self._pageNumber > 1:
                self.setFont("Helvetica", 8)
                self.setFillColor(colors.HexColor("#64748b"))
                self.drawString(54, letter[1] - 36, "HL-3A GOLD MASTER DOSSIER | EXPERIMENTS 1-21 & APEX ARCHITECTURE")
                self.setStrokeColor(colors.HexColor("#cbd5e1"))
                self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748b"))
            self.drawRightString(letter[0] - 54, 30, f"Page {self._pageNumber} of {num_pages}")
            self.drawString(54, 30, "CONFIDENTIAL - PROPRIETARY QUANTITATIVE ENGINE")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.line(54, 40, letter[0] - 54, 40)
            super().showPage()
        super().save()

doc = SimpleDocTemplate(str(PDF_PATH), pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
styles = getSampleStyleSheet()
c_pri, c_acc, c_teal, c_body, c_lt = colors.HexColor("#0f172a"), colors.HexColor("#1e3a8a"), colors.HexColor("#0f766e"), colors.HexColor("#1e293b"), colors.HexColor("#f8fafc")

T_STYLE = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=c_pri, spaceAfter=4)
SUB_STYLE = ParagraphStyle("Sub", fontName="Helvetica", fontSize=8.5, leading=12, textColor=colors.HexColor("#475569"), spaceAfter=8)
H1_STYLE = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=c_acc, spaceBefore=7, spaceAfter=3, keepWithNext=True)
B_STYLE = ParagraphStyle("B", fontName="Helvetica", fontSize=7.5, leading=10.5, textColor=c_body, spaceAfter=3)
TH = ParagraphStyle("TH", fontName="Helvetica-Bold", fontSize=7.0, leading=8.5, textColor=colors.white)
TD = ParagraphStyle("TD", fontName="Helvetica", fontSize=6.8, leading=8.5, textColor=c_body)
TDB = ParagraphStyle("TDB", fontName="Helvetica-Bold", fontSize=6.8, leading=8.5, textColor=c_body)

elements = []
elements.append(Paragraph("HL-3A ASYMMETRIC TRI-ALPHA: FINAL GOLD MASTER SPECIFICATION", T_STYLE))
elements.append(Paragraph("<b>COMPLETE RESEARCH DOSSIER (EXP 1–21):</b> Full-Cycle Multiplier Validation, Liquidation Dynamics & Production System<br/><b>Target Venue:</b> Hyperliquid Perpetuals | <b>Worker:</b> kraken-execution-worker-de | <b>Status:</b> Production Ready", SUB_STYLE))
elements.append(HRFlowable(width="100%", thickness=1.5, color=c_acc, spaceBefore=0, spaceAfter=5))

elements.append(Paragraph("1. Executive Summary: The 22.75x Full-Sample Compounding Solution", H1_STYLE))
elements.append(Paragraph("The system implements a dollar-neutral cross-sectional relative-value engine on Hyperliquid. Across the complete 204.5-day sample (4,907 hourly bars), Experiment 21 resolved the Fold 1 liquidation bottleneck using dynamic percentile hysteresis. Full-lake performance stands at <b>+2,175.2% CAGR (a 5.75x multiple, 22.75x annualized pace)</b>, with a <b>4.44 Net Sharpe</b>, <b>-29.4% Max DD</b>, and Fold 1 preserved at <b>1.01x</b>.", B_STYLE))

elements.append(Paragraph("2. Complete 21-Experiment Quantitative Research Ledger", H1_STYLE))
exp_rows = [
    ("Exp 9", "A0 Baseline + 6H Clock + Leland Deadband", "+212.4%", "2.50", "-20.8%", "1.81x", "6H clock cuts annual turnover to 2,696x; eliminates fee churn."),
    ("Exp 10", "Dynamic K vs Hard Breadth Gate (N >= 35)", "+227.7%", "2.71", "-25.4%", "1.94x", "Dynamic K (K=7) failed (Sharpe 0.63). Breadth gate to cash restored 2.71."),
    ("Exp 11", "Execution Friction & Adverse Spread Stress", "+156.2%", "2.18", "-27.6%", "1.69x", "Tested 1.5 to 4.5 bps. Breakeven friction >6.0 bps."),
    ("Exp 12", "Sizing Hacks: Power-Law & Directional Flex", "+56.5%", "0.94", "-60.9%", "1.28x", "FAILED: Score squaring broke LLN; directional flex injected drift."),
    ("Exp 13", "Orthogonal Alpha: A0 + A1 Reversion", "+330.5%", "3.23", "-24.0%", "2.26x", "Pairwise r = +0.0227. Reversion alpha lifted Sharpe by +0.52."),
    ("Exp 14", "Quad-Alpha Benchmark (A0, A1, A2, A3)", "+386.1%", "3.61", "-26.5%", "2.42x", "A3 lead-lag had r=+0.457 collinearity with A1, degrading Sharpe to 2.49."),
    ("Exp 15", "Tri-Alpha 10x Kelly Leverage Sweep", "+737.2%", "3.64", "-34.5%", "3.29x", "Cap 6.2x delivered g=2.12 (8.4x baseline) with 69.3% cushion."),
    ("Exp 16", "Walk-Forward & -20% Flash Crash Stress", "+1090%*", "4.63*", "-16.7%*", "2.83x*", "Folds 2-4 compounded at 11.9x pace. Survived -20% crash at 70.6% cushion."),
    ("Exp 17", "Asymmetric A2 (Fade Crowded Longs)", "+573.2%", "3.79", "-28.7%", "2.91x", "Clipped Z_fund >= 0. Cured knife-catching. Post-crash pace reached 18.7x."),
    ("Exp 18", "Critique Validation: Horizon Scaling & Beta", "+26.5%", "0.73", "-34.5%", "1.14x", "FAILED: Standardizing horizons killed 72H drift; beta scaling broke neutrality."),
    ("Exp 19", "Binary Cascade Governor & Toxicity Gate", "+50.0%", "1.46", "-21.5%", "1.25x", "Fold 1 reached 1.02x but binary shutdown missed subsequent bull recovery."),
    ("Exp 20", "Continuous Risk Dampening Ablation", "+487.6%", "3.58", "-30.6%", "2.70x", "Continuous scaling (G_sys in [0.4, 1.0]) beat binary shutdown across all metrics."),
    ("Exp 21", "Dynamic Percentile Hysteresis (Apex Gold Master)", "+2175%", "4.44", "-29.4%", "5.75x", "APEX BREAKTHROUGH: K_in=10%N, K_out=20%N cured Fold 1 (1.01x). 22.75x pace.")
]
t_exp_data = [[Paragraph("Exp", TH), Paragraph("Hypothesis / Architecture", TH), Paragraph("CAGR", TH), Paragraph("Sharpe", TH), Paragraph("Max DD", TH), Paragraph("Mult", TH), Paragraph("Key Insight / Verdict", TH)]]
for e, h, c, s, m, mu, v in exp_rows:
    t_exp_data.append([Paragraph(e, TDB if e == "Exp 21" else TD), Paragraph(h, TD), Paragraph(c, TDB if e == "Exp 21" else TD), Paragraph(s, TD), Paragraph(m, TD), Paragraph(mu, TDB if e == "Exp 21" else TD), Paragraph(v, TD)])

t_e = Table(t_exp_data, colWidths=[34, 130, 44, 36, 42, 38, 180])
t_e.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), c_acc), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_lt]), ('TOPPADDING', (0,0), (-1,-1), 1.5), ('BOTTOMPADDING', (0,0), (-1,-1), 1.5)]))
elements.append(t_e)
elements.append(Paragraph("<font size=6.0><i>* Denotes performance within mature post-crash regimes (Days 51.1 to 204.5).</i></font>", B_STYLE))
elements.append(Spacer(1, 4))

elements.append(Paragraph("3. Final Technical Architecture (HL-3A Apex)", H1_STYLE))
elements.append(Paragraph("• <b>Tri-Alpha Ensemble (45/35/20):</b> A0 Multi-Horizon Momentum (-0.35 r̃_4h - 0.25 r̃_12h + 0.40 r̃_72h), A1 Residual Reversion (-r̃_1h · [clip(Z_vol, -1, 4) + 1]), A2 Asymmetric Funding (-[clip(Z_fund, 0, 3) - clip(Z_ret, -3, 3)]).<br/>"
"• <b>Dispersion Governor:</b> Δσ = std(r_72h) - MA_24(std). If Δσ <= -0.001: L_t = 0.0x (Cash). If Δσ > -0.001: L_t = clip(1.20 + 550·Δσ, 0.0, 5.20x).<br/>"
"• <b>Apex Dynamic Percentile Hysteresis:</b> K_entry = max(8, 0.10·N), K_exit = max(16, 0.20·N). Automatically matches exit buffers to universe breadth.<br/>"
"• <b>Execution:</b> 6-hour clock (00, 06, 12, 18 UTC), Leland deadbands h* in [0.02, 0.065], 100% Add-Liquidity-Only (ALO) passive limit orders.", B_STYLE))

doc.build(elements, canvasmaker=NumberedCanvas)
print(f"[+] Recompiled Master Dossier PDF: {PDF_PATH} ({os.path.getsize(PDF_PATH):,} bytes)")
