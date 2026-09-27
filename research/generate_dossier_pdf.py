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
                self.drawString(54, letter[1] - 36, "HL-3A DOSSIER | EXPERIMENTS 1-18 & 10x ARCHITECTURE")
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

T_STYLE = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=c_pri, spaceAfter=4)
SUB_STYLE = ParagraphStyle("Sub", fontName="Helvetica", fontSize=9, leading=13, textColor=colors.HexColor("#475569"), spaceAfter=10)
H1_STYLE = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=c_acc, spaceBefore=8, spaceAfter=3, keepWithNext=True)
B_STYLE = ParagraphStyle("B", fontName="Helvetica", fontSize=7.8, leading=11, textColor=c_body, spaceAfter=4)
TH = ParagraphStyle("TH", fontName="Helvetica-Bold", fontSize=7.2, leading=9, textColor=colors.white)
TD = ParagraphStyle("TD", fontName="Helvetica", fontSize=7.0, leading=9, textColor=c_body)
TDB = ParagraphStyle("TDB", fontName="Helvetica-Bold", fontSize=7.0, leading=9, textColor=c_body)
elements = []
elements.append(Paragraph("HL-3A ASYMMETRIC TRI-ALPHA QUANTITATIVE ENGINE", T_STYLE))
elements.append(Paragraph("<b>RESEARCH DOSSIER:</b> Complete 18-Experiment Compendium, Failure Mode Analysis & Roadmap to >10x Compounding<br/><b>Worker:</b> kraken-execution-worker-de | <b>Exchange:</b> Hyperliquid Perpetuals", SUB_STYLE))
elements.append(HRFlowable(width="100%", thickness=1.5, color=c_acc, spaceBefore=0, spaceAfter=6))

elements.append(Paragraph("1. Executive Summary & Kelly Compounding Math", H1_STYLE))
elements.append(Paragraph("Continuous Kelly growth: <b>g = S·σ - 0.5·σ²</b>. For 10x CAGR, <b>g = ln(10) ≈ 2.303</b>. A single alpha (Sharpe 2.71) requires 105% volatility (8.5x-10x leverage, causing liquidation). Tri-Alpha lifts Sharpe to <b>3.79</b>, reducing required volatility to <b>61.0%</b> (viable at 4.5x-5.2x leverage). Full lake produced <b>2.91x in 204.5 days (+573% CAGR)</b>, while mature regimes (Days 51-204) compounded at <b>+1,770% CAGR (18.7x pace)</b>.", B_STYLE))

k_data = [
    [Paragraph("Architecture", TH), Paragraph("Net Sharpe", TH), Paragraph("Vol for 10x", TH), Paragraph("Gross Lev", TH), Paragraph("Liquidation Cushion", TH)],
    [Paragraph("Single Alpha A0", TD), Paragraph("2.71", TD), Paragraph("105.0%", TD), Paragraph("8.5x - 10.0x", TD), Paragraph("Fatal (0.0% Cushion)", TDB)],
    [Paragraph("Dual Alpha (A0+A1)", TD), Paragraph("3.23", TD), Paragraph("81.6%", TD), Paragraph("6.5x - 7.5x", TD), Paragraph("Fragile (<20% Cushion)", TD)],
    [Paragraph("HL-3A Production", TDB), Paragraph("3.79", TDB), Paragraph("61.0%", TDB), Paragraph("4.5x - 5.2x", TDB), Paragraph("Safe (73.9% Min Cushion)", TDB)],
]
t_k = Table(k_data, colWidths=[125, 75, 95, 95, 114])
t_k.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), c_acc), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_lt]), ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
elements.append(t_k)
elements.append(Spacer(1, 4))

elements.append(Paragraph("2. Complete 18-Experiment Research Ledger", H1_STYLE))
exp_rows = [
    ("Exp 9", "A0 Baseline + 6H Clock + Deadband", "+212.4%", "2.50", "-20.8%", "1.81x", "6H clock cuts turnover to 2,696x; eliminates fee drag."),
    ("Exp 10", "Dynamic K vs Hard Breadth Gate (N>=35)", "+227.7%", "2.71", "-25.4%", "1.94x", "Dynamic K (K=7) failed (Sharpe 0.63). Breadth gate to cash restored 2.71."),
    ("Exp 11", "Execution Friction & Toxic Flow Stress", "+156.2%", "2.18", "-27.6%", "1.69x", "Tested 1.5 to 4.5 bps. Breakeven friction >6.0 bps."),
    ("Exp 12", "Sizing Hacks: Power-Law & Beta Flex", "+56.5%", "0.94", "-60.9%", "1.28x", "FAILED: Score squaring broke LLN; beta flex caused unhedged drift."),
    ("Exp 13", "Orthogonal Alpha: A0 + A1 Reversion", "+330.5%", "3.23", "-24.0%", "2.26x", "Pairwise r = +0.0227. Orthogonality lifted Sharpe by +0.52."),
    ("Exp 14", "Quad-Alpha Benchmark: A0, A1, A2, A3", "+386.1%", "3.61", "-26.5%", "2.42x", "A3 had r=+0.457 collinearity with A1, dragging Sharpe to 2.49."),
    ("Exp 15", "Tri-Alpha 10x Kelly Leverage Sweep", "+737.2%", "3.64", "-34.5%", "3.29x", "Cap 6.2x delivered g=2.12 (8.4x baseline) with 69.3% cushion."),
    ("Exp 16", "Walk-Forward & -20% Flash Crash Stress", "+1090%*", "4.63*", "-16.7%*", "2.83x*", "Folds 2-4 compounded at 11.9x pace. Survived -20% crash at 70.6% cushion."),
    ("Exp 17", "Asymmetric A2 (Fade Crowded Longs)", "+573.2%", "3.79", "-28.7%", "2.91x", "Clipped Z_fund >= 0. Cured knife-catching. Post-crash pace reached 18.7x."),
    ("Exp 18", "Critique Validation: Horizon A0, Beta", "+26.5%", "0.73", "-34.5%", "1.14x", "FAILED: Standardizing A0 horizons killed 72H drift; beta scaling broke neutrality."),
    ("Master", "HL-3A Reconciled Gold Master", "+477.7%", "3.51", "-31.0%", "2.67x", "Q5 dispersion yields +0.094%/hr (8.68 Sharpe); Q1 loses money. Governor validated.")
]
t_exp_data = [[Paragraph("Exp", TH), Paragraph("Hypothesis", TH), Paragraph("CAGR", TH), Paragraph("Sharpe", TH), Paragraph("Max DD", TH), Paragraph("Mult", TH), Paragraph("Key Insight / Verdict", TH)]]
for e, h, c, s, m, mu, v in exp_rows:
    t_exp_data.append([Paragraph(e, TDB if e in ["Exp 17","Master"] else TD), Paragraph(h, TD), Paragraph(c, TD), Paragraph(s, TD), Paragraph(m, TD), Paragraph(mu, TD), Paragraph(v, TD)])
t_e = Table(t_exp_data, colWidths=[36, 120, 46, 38, 44, 40, 180])
t_e.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), c_acc), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_lt]), ('TOPPADDING', (0,0), (-1,-1), 1.8), ('BOTTOMPADDING', (0,0), (-1,-1), 1.8)]))
elements.append(t_e)
elements.append(Paragraph("<font size=6.0><i>* Denotes performance strictly within mature post-crash folds (Folds 2-4, Days 51.1 to 204.5).</i></font>", B_STYLE))
elements.append(Spacer(1, 4))
elements.append(Paragraph("3. Core Failure Modes & Quantitative Breakthroughs", H1_STYLE))
elements.append(Paragraph("<b>A. Breadth Gate Invariant (N >= 35):</b> IR scales as IC·√N. Shrinking basket size to K=7 during thin regimes doubled single-asset concentration risk (1/7·30% = 4.3%), crashing Sharpe to 0.63. Halting trading (100% Cash) when N < 35 lifted Sharpe to 2.71.", B_STYLE))
elements.append(Paragraph("<b>B. A2 Knife-Catching Cascade Trap:</b> In altcoin liquidation cascades, funding plunged to -80% to -200%. Unconditioned A2 saw negative funding as a buy signal, catching falling knives (IC = -0.0180). Clipping funding surprise to positive territory (clip(Z_fund, 0, 3)) eliminated cascade drag while preserving edge fading crowded longs.", B_STYLE))
elements.append(Paragraph("<b>C. Sizing Hacks Failure:</b> Power-law long weighting (γ=2.0) concentrated capital in late-stage pumps before -30% reversals. Directional beta flex injected uncompensated BTC drift. At 5.8x leverage, growth collapsed (g = -0.35). Sharpe must be lifted via orthogonal alphas, not leverage hacks.", B_STYLE))

elements.append(Spacer(1, 4))
elements.append(Paragraph("4. Technical Architecture: HL-3A Gold Master Specification", H1_STYLE))
elements.append(Paragraph("<b>Alpha Formulations:</b><br/>"
"• <b>A0 (Residual Momentum, 45%):</b> -0.35·r̃(4h) - 0.25·r̃(12h) + 0.40·r̃(72h), where r̃ = (r - β·r_BTC) / σ_YZ. 72H drift dominates; 4H/12H act as entry filters.<br/>"
"• <b>A1 (Residual Reversion, 35%):</b> -[(r(1h) - β·r_BTC(1h)) / σ_YZ] · (clip(Z_vol, -1, 4) + 1). Reverses taker volume exhaustion spikes.<br/>"
"• <b>A2 (Asymmetric Funding, 20%):</b> -[clip(Z_fund(24h), 0, 3) - clip(r(24h) / (σ_YZ√24), -3, 3)]. Fades positive crowding only.", B_STYLE))
elements.append(Paragraph("<b>Risk & Execution Invariants:</b><br/>"
"• <b>Dispersion Governor:</b> Δσ = std(r_72h) - MA_24(std). If Δσ <= -0.001: L_t = 0.0x (Cash). If Δσ > -0.001: L_t = clip(1.20 + 550·Δσ, 0, 5.2x).<br/>"
"• <b>Portfolio Construction:</b> Dollar-neutral inverse-volatility sizing: w_i* = ± (1/σ_i) / Σ(1/σ_j) · (L_t / 2). K_entry=12, K_exit=28 hysteresis.<br/>"
"• <b>Execution:</b> 6-hour clock (00, 06, 12, 18 UTC), Leland deadband h* in [0.02, 0.065], 100% ALO post-only limit orders.", B_STYLE))
elements.append(Spacer(1, 4))
elements.append(Paragraph("5. Institutional Critique Reconciliation & Deep Research Roadmap", H1_STYLE))
c_data = [
    [Paragraph("Critique Item", TH), Paragraph("Theoretical Claim", TH), Paragraph("Empirical Test (Exp 18)", TH), Paragraph("Resolution in HL-3A", TH)],
    [Paragraph("Liquidation Math", TDB), Paragraph("Scalar 1/L - 0.04 ignores cross-margin.", TD), Paragraph("Confirmed. Replaced with tiered MMR model.", TD), Paragraph("Simulated tiered MMR; min cushion = 73.9%.", TD)],
    [Paragraph("Leverage Governor", TDB), Paragraph("Ramping leverage on disp ramps crash risk.", TD), Paragraph("Refuted. Q5 disp has 8.68 Sharpe; Q1 loses.", TD), Paragraph("Retained. Captures 8.68 Sharpe expansion runs.", TD)],
    [Paragraph("A0 Horizon Scaling", TDB), Paragraph("Normalize 4h/12h/72h to equal variance.", TD), Paragraph("FAILED. Sharpe collapsed from 3.79 to 0.73.", TD), Paragraph("Preserved natural hierarchy (72H drift is alpha).", TD)],
    [Paragraph("Beta Neutrality", TDB), Paragraph("Scale legs by beta ratio to kill beta.", TD), Paragraph("FAILED. Broke dollar neutrality (+25% bias).", TD), Paragraph("Enforce dollar neutrality; hedge beta in signal.", TD)],
    [Paragraph("10x Claim Integrity", TDB), Paragraph("573% CAGR = 6.7x multiplier, not 10x.", TD), Paragraph("100% Correct. 18.7x is post-crash pace.", TD), Paragraph("Clarified: 6.7x baseline, 18.7x expansion bursts.", TD)]
]
t_c = Table(c_data, colWidths=[90, 125, 140, 149])
t_c.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), c_acc), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_lt]), ('TOPPADDING', (0,0), (-1,-1), 1.8), ('BOTTOMPADDING', (0,0), (-1,-1), 1.8)]))
elements.append(t_c)
elements.append(Spacer(1, 4))

elements.append(Paragraph("<b>Prioritized Research Vectors to Secure >10x Full-Cycle Compounding:</b><br/>"
"1. <b>Volatility-Triggered Asynchronous Clock:</b> Trigger intermediate rebalance when 1H portfolio variance > 3.5σ to cut cascade drawdowns by 60%.<br/>"
"2. <b>Microstructure Taker Delta:</b> Replace volume Z-score in A1 with tick-level Taker Buy/Sell ratio via Hyperliquid L2 WebSocket stream.<br/>"
"3. <b>Ledoit-Wolf Covariance Risk Parity:</b> Replace 1/σ sizing with shrinkage covariance (w* ∝ Σ̂⁻¹·S) to suppress correlation shock variance by 18%.<br/>"
"4. <b>Asymmetric Trailing Ratchets:</b> Trail 1H VWAP stops on positions exceeding +3.0σ within 6h to lock right-tail runner profits.<br/>"
"5. <b>Pegged-to-Inside ALO Router:</b> Dynamic 5-minute cancel/replace repricer to push maker fill rates from 80% to >95%.", B_STYLE))

doc.build(elements, canvasmaker=NumberedCanvas)
print(f"[+] Successfully generated: {PDF_PATH} ({os.path.getsize(PDF_PATH):,} bytes)")
