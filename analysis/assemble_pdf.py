#!/usr/bin/env python3
"""
Generate a PDF version of the revised paper directly using reportlab.
Reads the .docx to extract text/structure and renders to PDF with
proper formatting, embedded tables, and figures.

Usage:
    python assemble_pdf.py
"""

import csv
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.colors import black, grey
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Times New Roman TTF fonts for full Unicode support (macrons,
# em-dashes, etc.).  Search platform-specific font directories; fall back to
# reportlab's built-in "Times-Roman" family if TTFs are not found.
import platform as _platform

def _find_font_dir() -> Path | None:
    """Return the directory containing Times New Roman .ttf files, or None."""
    candidates: list[Path] = []
    _sys = _platform.system()
    if _sys == "Darwin":
        candidates = [
            Path("/System/Library/Fonts/Supplemental"),
            Path("/Library/Fonts"),
            Path.home() / "Library" / "Fonts",
        ]
    elif _sys == "Linux":
        candidates = [
            Path("/usr/share/fonts/truetype/msttcorefonts"),
            Path("/usr/share/fonts/TTF"),
            Path("/usr/share/fonts/truetype"),
            Path.home() / ".local" / "share" / "fonts",
        ]
    elif _sys == "Windows":
        candidates = [Path("C:/Windows/Fonts")]
    for d in candidates:
        if (d / "Times New Roman.ttf").is_file():
            return d
        # Linux packages sometimes use lowercase filenames
        if (d / "times.ttf").is_file():
            return d
    return None

_FONT_DIR = _find_font_dir()
if _FONT_DIR is not None:
    # Accommodate lowercase filenames (common on Linux ttf-mscorefonts)
    def _ttf(name: str) -> str:
        p = _FONT_DIR / name
        if p.is_file():
            return str(p)
        return str(_FONT_DIR / name.lower().replace(" ", ""))

    pdfmetrics.registerFont(TTFont("TNR", _ttf("Times New Roman.ttf")))
    pdfmetrics.registerFont(TTFont("TNR-Bold", _ttf("Times New Roman Bold.ttf")))
    pdfmetrics.registerFont(TTFont("TNR-Italic", _ttf("Times New Roman Italic.ttf")))
    pdfmetrics.registerFont(TTFont("TNR-BI", _ttf("Times New Roman Bold Italic.ttf")))
    pdfmetrics.registerFontFamily(
        "TNR", normal="TNR", bold="TNR-Bold", italic="TNR-Italic", boldItalic="TNR-BI"
    )
else:
    import warnings
    warnings.warn(
        "Times New Roman .ttf files not found; falling back to built-in "
        "Times-Roman (limited Unicode support). Install ttf-mscorefonts on "
        "Linux or ensure Times New Roman is available.",
        stacklevel=2,
    )
    # Map "TNR" family to reportlab built-in PostScript fonts so the rest
    # of the code can reference "TNR" uniformly.
    from reportlab.lib.fonts import addMapping
    addMapping("TNR", 0, 0, "Times-Roman")
    addMapping("TNR", 1, 0, "Times-Bold")
    addMapping("TNR", 0, 1, "Times-Italic")
    addMapping("TNR", 1, 1, "Times-BoldItalic")

BASE = Path(__file__).parent.parent
TABLE_DIR = BASE / "tables"
FIG_DIR = BASE / "figures"
OUT_PATH = BASE / "Underpaid_to_Measure_revised.pdf"


def get_styles():
    """Create custom paragraph styles."""
    ss = getSampleStyleSheet()

    styles = {}
    styles["title"] = ParagraphStyle(
        "Title", parent=ss["Title"],
        fontName="TNR-Bold", fontSize=16,
        alignment=TA_CENTER, spaceAfter=12, leading=20,
    )
    styles["author"] = ParagraphStyle(
        "Author", parent=ss["Normal"],
        fontName="TNR", fontSize=13,
        alignment=TA_CENTER, spaceAfter=6,
    )
    styles["affil"] = ParagraphStyle(
        "Affil", parent=ss["Normal"],
        fontName="TNR-Italic", fontSize=12,
        alignment=TA_CENTER, spaceAfter=6,
    )
    styles["date"] = ParagraphStyle(
        "Date", parent=ss["Normal"],
        fontName="TNR", fontSize=12,
        alignment=TA_CENTER, spaceAfter=24,
    )
    styles["jel"] = ParagraphStyle(
        "JEL", parent=ss["Normal"],
        fontName="TNR", fontSize=11,
        alignment=TA_CENTER, spaceAfter=4,
    )
    styles["h1"] = ParagraphStyle(
        "H1", parent=ss["Heading1"],
        fontName="TNR-Bold", fontSize=14,
        spaceBefore=18, spaceAfter=8, leading=18,
        textColor=black,
    )
    styles["h2"] = ParagraphStyle(
        "H2", parent=ss["Heading2"],
        fontName="TNR-Bold", fontSize=12,
        spaceBefore=14, spaceAfter=6, leading=16,
        textColor=black,
    )
    styles["h3"] = ParagraphStyle(
        "H3", parent=ss["Heading3"],
        fontName="TNR-BI", fontSize=11,
        spaceBefore=10, spaceAfter=4, leading=14,
        textColor=black,
    )
    styles["body"] = ParagraphStyle(
        "Body", parent=ss["Normal"],
        fontName="TNR", fontSize=11,
        alignment=TA_JUSTIFY,
        spaceBefore=2, spaceAfter=6, leading=15,
        firstLineIndent=24,
    )
    styles["body_first"] = ParagraphStyle(
        "BodyFirst", parent=styles["body"],
        firstLineIndent=0,
    )
    styles["equation"] = ParagraphStyle(
        "Equation", parent=ss["Normal"],
        fontName="TNR-Italic", fontSize=10,
        alignment=TA_CENTER,
        spaceBefore=6, spaceAfter=6, leading=14,
    )
    styles["caption"] = ParagraphStyle(
        "Caption", parent=ss["Normal"],
        fontName="TNR-Italic", fontSize=10,
        alignment=TA_CENTER,
        spaceBefore=4, spaceAfter=12, leading=13,
    )
    styles["table_caption"] = ParagraphStyle(
        "TableCaption", parent=ss["Normal"],
        fontName="TNR-Bold", fontSize=10,
        alignment=TA_CENTER,
        spaceBefore=8, spaceAfter=4,
    )
    styles["note"] = ParagraphStyle(
        "Note", parent=ss["Normal"],
        fontName="TNR-Italic", fontSize=9,
        alignment=TA_LEFT,
        spaceBefore=2, spaceAfter=8, leading=12,
    )
    styles["ref"] = ParagraphStyle(
        "Ref", parent=ss["Normal"],
        fontName="TNR", fontSize=10,
        alignment=TA_LEFT,
        spaceBefore=0, spaceAfter=4, leading=13,
        leftIndent=36, firstLineIndent=-36,
    )
    return styles


def add_csv_table(story, csv_path, caption, styles, col_widths=None):
    """Read CSV and add as formatted table."""
    with open(csv_path) as f:
        rows = list(csv.reader(f))
    if not rows:
        return

    story.append(Paragraph(caption, styles["table_caption"]))

    # Format cells as Paragraphs for wrapping
    cell_style = ParagraphStyle(
        "Cell", fontName="TNR", fontSize=9, leading=11,
    )
    header_style = ParagraphStyle(
        "CellH", fontName="TNR-Bold", fontSize=9, leading=11,
    )

    table_data = []
    for i, row in enumerate(rows):
        st = header_style if i == 0 else cell_style
        table_data.append([Paragraph(c.strip(), st) for c in row])

    if col_widths is None:
        avail = 6.5 * inch
        col_widths = [avail / len(rows[0])] * len(rows[0])

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, grey),
        ("BACKGROUND", (0, 0), (-1, 0), "#E8E8E8"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))


def add_figure(story, img_path, caption, styles, width=5.0):
    """Add image with caption."""
    if not img_path.exists():
        story.append(Paragraph(f"[FIGURE NOT FOUND: {img_path.name}]", styles["body"]))
        return
    story.append(Spacer(1, 6))
    img = Image(str(img_path), width=width * inch)
    img.hAlign = "CENTER"
    # Compute height to maintain aspect ratio
    from reportlab.lib.utils import ImageReader
    ir = ImageReader(str(img_path))
    iw, ih = ir.getSize()
    aspect = ih / iw
    img._height = width * inch * aspect
    story.append(img)
    story.append(Paragraph(caption, styles["caption"]))


def build_story(styles):
    """Build the full document as a list of flowables."""
    S = styles
    story = []

    # ---- TITLE PAGE ----
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph(
        "Underpaid to Measure? Efficiency Wages and<br/>"
        "Data Quality in the National Forest Inventory",
        S["title"]
    ))
    story.append(Spacer(1, 24))
    story.append(Paragraph("Martin Hensley", S["author"]))
    story.append(Paragraph("Independent Researcher", S["affil"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("March 2026", S["date"]))
    story.append(Spacer(1, 24))
    story.append(Paragraph(
        "<b>Keywords:</b> efficiency wages, moral hazard, forest inventory, "
        "data quality, ocular estimation, principal-agent, FIA", S["jel"]
    ))
    story.append(Paragraph("<b>JEL Classification:</b> J41, Q23, D82, D83, Q28", S["jel"]))
    story.append(PageBreak())

    # ---- ABSTRACT ----
    story.append(Paragraph("Abstract", S["h1"]))
    story.append(Paragraph(
        "Using paired QA/production measurements of 94,459 trees across 24 northern "
        "states (Yanai et al., 2023), we find that production field crews in the USDA "
        "Forest Inventory and Analysis (FIA) program record ocular estimation for "
        "23.1% of tree heights versus 5.8% for QA crews \u2014 a 4:1 ratio providing "
        "direct evidence of differential measurement effort under different "
        "institutional conditions. Height discrepancies between crew types are "
        "dramatic (mean |diff| = 3.31 ft) while diameter discrepancies are minimal "
        "(0.055 in.), consistent with effort reduction concentrating on the "
        "hard-to-verify margin as predicted by multi-task moral hazard theory "
        "(Holmstr\u00f6m and Milgrom, 1991). The estimation differential is pervasive "
        "year-round rather than concentrated in late-season months \u2014 consistent "
        "with the finite-horizon prediction that terminal seasonal workers face "
        "violated incentive constraints throughout their appointment, not only at "
        "season\u2019s end.",
        S["body_first"]
    ))
    story.append(Paragraph(
        "A supporting efficiency wage calibration (Shapiro and Stiglitz, 1984) using "
        "federal pay schedules, stated quality assurance audit rates, and competing "
        "labor market wages shows that the no-shirking condition (NSC) substantially "
        "exceeds current technician wages under central parameter assumptions, though "
        "the magnitude of the gap is sensitive to the effort cost parameter, which "
        "has the weakest direct empirical grounding. The calibrated model identifies "
        "low effective detection probability as the parameter most strongly governing "
        "the incentive gap and shows that increasing effective detection probability "
        "through expanded audits and technology-assisted monitoring is substantially "
        "more cost-effective than raising wages within the General Schedule structure.",
        S["body"]
    ))
    story.append(PageBreak())

    # ---- 1. INTRODUCTION ----
    story.append(Paragraph("1. Introduction", S["h1"]))

    intro_paras = [
        "The United States Forest Inventory and Analysis (FIA) program is the "
        "nation\u2019s continuous forest census \u2014 a systematic inventory of trees "
        "across all ownerships that supports approximately $80 billion in annual "
        "timber commerce, informs national carbon accounting, and underpins forest "
        "management decisions at every scale from timber sales to climate policy. "
        "The program employs several hundred seasonal field technicians each year "
        "to visit a nationally representative sample of approximately 130,000 "
        "permanent plots on a rotating five- to ten-year cycle, measuring individual "
        "tree diameters, heights, species, and condition. The integrity of this "
        "information infrastructure depends almost entirely on the accuracy of "
        "these field measurements.",

        "This paper examines whether the institutional design of the FIA program "
        "creates conditions under which rational field technicians would "
        "systematically approximate measurements \u2014 substituting ocular estimates "
        "for instrument-based measurements. Using paired QA/production data from "
        "Yanai et al. (2023) \u2014 94,459 trees across 24 states measured "
        "independently by both production and QA crews \u2014 we find that production "
        "crews self-report ocular estimation (HTCD=3) for 23.1% of heights, "
        "compared to 5.8% for QA crews. This 4:1 ratio, recorded in literal "
        "method codes rather than inferred from statistical forensics, provides "
        "direct evidence that measurement effort differs systematically across "
        "institutional conditions.",

        "We make three contributions. First, we document differential estimation "
        "across crew types using paired QA/production data, providing the most "
        "direct evidence to date that FIA production crews use ocular estimation "
        "at substantially elevated rates. The height-diameter asymmetry in "
        "measurement discrepancies \u2014 dramatic for heights, minimal for diameters "
        "\u2014 confirms that effort reduction concentrates on the hard-to-verify "
        "margin, as multi-task moral hazard theory predicts (Holmstr\u00f6m and "
        "Milgrom, 1991).",

        "Second, we develop a principal-agent model drawing on the efficiency wage "
        "framework of Shapiro and Stiglitz (1984) as a motivating benchmark for "
        "interpreting these findings. The calibrated no-shirking condition (NSC) "
        "identifies the institutional parameters governing incentive alignment "
        "\u2014 particularly the low effective detection probability \u2014 and "
        "provides quantitative targets for policy intervention.",

        "Third, we derive specific policy recommendations from the calibrated "
        "model: monitoring intensities, institutional reforms, and "
        "technology-assisted verification approaches that would narrow the gap "
        "between production and QA measurement conditions.",

        "Our analysis connects to the economics of monitoring and incentives "
        "(Shapiro and Stiglitz, 1984; Holmstr\u00f6m, 1979; Holmstr\u00f6m and "
        "Milgrom, 1991), the intrinsic motivation literature (B\u00e9nabou and "
        "Tirole, 2003, 2006), and natural resource monitoring, where Duflo et "
        "al. (2013) demonstrate experimentally that auditor incentive design "
        "dramatically affects environmental compliance reporting in India. "
        "To our knowledge, this paper represents a novel application of the "
        "Shapiro-Stiglitz efficiency wage framework specifically to natural "
        "resource data collection programs, complementing the Duflo et al. "
        "focus on third-party auditing.",

        "The remainder of the paper is organized as follows. Section 2 provides "
        "institutional background and develops the motivating theoretical "
        "framework. Section 3 presents the empirical analysis. Section 4 discusses "
        "implications for timber markets and data governance. Section 5 derives "
        "policy recommendations. Section 6 discusses limitations, and Section 7 "
        "concludes.",
    ]
    for i, p in enumerate(intro_paras):
        story.append(Paragraph(p, S["body_first"] if i == 0 else S["body"]))

    # ---- 2. INSTITUTIONAL BACKGROUND AND THEORETICAL FRAMEWORK ----
    story.append(Paragraph("2. Institutional Background and Theoretical Framework", S["h1"]))

    story.append(Paragraph("2.1 The FIA Program", S["h2"]))
    bg_paras = [
        "The Forest Inventory and Analysis program, administered by the USDA "
        "Forest Service, conducts the national forest inventory mandated by the "
        "Forest and Rangeland Renewable Resources Research Act of 1978. Since the "
        "transition from periodic to annual inventory in the early 2000s, FIA has "
        "operated a panel-based sampling design in which approximately one-fifth "
        "to one-seventh of permanent plot locations are visited each year. The "
        "national plot network consists of approximately 130,000 permanent sample "
        "plots (Bechtold and Patterson, 2005).",

        "Each plot consists of four circular subplots (24-foot radius for trees "
        "\u22655.0 inches DBH). Field crews measure diameter at breast height (DBH) "
        "with a diameter tape to 0.1 inch, total height with a clinometer or laser "
        "hypsometer to the nearest foot, species identification, and numerous "
        "auxiliary variables. A single plot typically requires 4\u20138 hours. The "
        "measurement season runs roughly April through November.",
    ]
    for i, p in enumerate(bg_paras):
        story.append(Paragraph(p, S["body_first"] if i == 0 else S["body"]))

    story.append(Paragraph("2.2 Quality Assurance Structure", S["h2"]))
    qa_paras = [
        "FIA operates a two-tier quality assurance program. <i>Hot checks</i> are "
        "supervisory observations where a crew leader accompanies a technician "
        "\u2014 these are not independent. <i>Blind checks</i> are independent "
        "re-measurements where a separate QA crew revisits a randomly selected "
        "production plot without the original crew\u2019s knowledge. The stated target "
        "is approximately 4% of production plots per year (USDA Forest Service, 2023).",

        "From the technician\u2019s perspective, the effective detection probability "
        "is the product of the probability of plot selection for QA, the probability "
        "of timely re-measurement, and the probability of detecting approximation "
        "conditional on occurrence. Even at 4%, this compound probability is "
        "substantially less than 0.04 per plot-period.",
    ]
    for i, p in enumerate(qa_paras):
        story.append(Paragraph(p, S["body_first"] if i == 0 else S["body"]))

    story.append(Paragraph("2.3 The Seasonal Labor Market", S["h2"]))
    labor_paras = [
        "FIA field crews are predominantly seasonal (term) federal employees at "
        "GS-4 through GS-6 pay grades. Term appointments under 5 CFR \u00a7316.401 "
        "are limited to 13 months with no rehire guarantee. This creates three "
        "incentive-relevant features: (1) the outside option includes competitive "
        "seasonal outdoor employment (wildfire crews at higher pay, trail maintenance, "
        "NPS/BLM positions), with BLS data showing geographic variation from $15/hr "
        "(Southeast) to $22/hr (Pacific Northwest); (2) the guaranteed end of "
        "appointment undermines the termination threat as the season progresses; "
        "and (3) mid-season termination faces practical barriers including "
        "documentation requirements and progressive discipline expectations.",
    ]
    for p in labor_paras:
        story.append(Paragraph(p, S["body_first"]))

    # ---- 2.4 A MOTIVATING MODEL ----
    story.append(Paragraph("2.4 A Motivating Model", S["h2"]))
    story.append(Paragraph(
        "We use the Shapiro-Stiglitz (1984) efficiency wage framework as a "
        "quantitative lens for assessing whether institutional design creates "
        "conditions favoring measurement approximation \u2014 not a causal claim "
        "about why the HTCD differential documented in Section 3 exists. The "
        "calibration provides an indicative benchmark for the magnitude of a "
        "potential incentive gap, not the precise behavioral mechanism through "
        "which that gap translates into measurement decisions.",
        S["body_first"]
    ))
    story.append(Paragraph(
        "A risk-neutral field technician employed at wage <i>w</i> per period "
        "chooses effort <i>e</i> \u2208 {0, \u0113}: careful measurement "
        "(<i>e</i> = \u0113, disutility \u0113) or approximation (<i>e</i> = 0). "
        "The principal detects approximation with probability <i>q</i> per period "
        "through QA audits; detection leads to termination. With exogenous "
        "separation rate <i>b</i> and discount rate <i>r</i>, the standard value "
        "function analysis yields the no-shirking condition (NSC). Intuitively, if "
        "workers can cut corners without being caught, they will only refrain if the "
        "job pays enough above their next-best option to make the risk of termination "
        "costly. The minimum wage that makes honest effort worthwhile is:",
        S["body"]
    ))
    story.append(Paragraph(
        "w* \u2265 w\u0305 + \u0113 + (\u0113/q)(r + b)",
        S["equation"]
    ))
    story.append(Paragraph(
        "The critical wage has three components: the outside option w\u0305; a "
        "compensating differential for effort \u0113; and the efficiency wage "
        "premium (\u0113/<i>q</i>)(<i>r</i> + <i>b</i>) \u2014 the extra pay "
        "needed to make the job valuable enough that workers fear losing it. "
        "This premium is large when detection is infrequent (<i>q</i> small), "
        "the job is ending soon (<i>b</i> large), or the discount rate is high. "
        "Risk aversion would increase the NSC, so our risk-neutral specification "
        "is conservative.",
        S["body"]
    ))
    story.append(Paragraph(
        "<b>Finite-horizon extension.</b> The stationary SS model assumes a "
        "constant hazard of termination, whereas seasonal FIA employment "
        "has a known endpoint. In a finite-horizon setting, the termination "
        "threat is vacuous in the final period \u2014 the worker is leaving "
        "regardless \u2014 and by backward induction, the NSC is violated "
        "in every period. The standard resolution in the repeated-game "
        "literature is that reputation or continuation value sustains "
        "cooperation, but these mechanisms require that the employment "
        "relationship extends beyond the current season. For a purely "
        "terminal seasonal worker with no prospect of rehire, backward "
        "induction implies that estimation is rational throughout the "
        "appointment, not merely at season\u2019s end. This is actually "
        "more consistent with the empirical finding of year-round "
        "estimation (Section 3.2) than the stationary model, which would "
        "predict late-season concentration as the effective separation "
        "rate <i>b</i> increases. We therefore interpret the calibration "
        "as a benchmark indicating the direction and magnitude of "
        "incentive gaps, not as a precise wage threshold.",
        S["body"]
    ))
    story.append(Paragraph(
        "For career-track workers \u2014 GS-0462 technicians pursuing "
        "permanent GS-0460 positions through the "
        "GS-4\u2192GS-5\u2192GS-7 pipeline \u2014 the employment "
        "relationship is effectively indefinite-horizon with periodic "
        "re-contracting. The substantial employment rents of permanent "
        "federal service (FERS retirement, FEHB health insurance, job "
        "security) create continuation value that sustains cooperation "
        "across seasons. For this subpopulation, the stationary SS "
        "framework is a reasonable approximation: the multi-season career "
        "structure means the repeated-game logic applies over a multi-year "
        "horizon. The calibrated NSC therefore applies most directly to "
        "terminal seasonals without career pathways \u2014 the vulnerable "
        "margin where neither backward induction nor career incentives "
        "sustain measurement effort.",
        S["body"]
    ))

    story.append(Paragraph(
        "We calibrate the NSC using FIA institutional data, federal pay schedules, "
        "and labor market statistics. Table 1 summarizes parameter values.",
        S["body"]
    ))

    add_csv_table(story, TABLE_DIR / "table1_parameters.csv",
                  "Table 1: Model Parameters and Sources", S,
                  col_widths=[1.6*inch, 1.2*inch, 1.0*inch, 2.7*inch])

    story.append(Paragraph(
        "At central parameters (w\u0305 = $16, \u0113 = $4.32, <i>q</i> = 0.01, "
        "<i>r</i> = 0.004, <i>b</i> = 0.02): w* = 16 + 4.32 + (4.32/0.01)(0.024) "
        "= <b>$30.69/hr</b> \u2014 78% above GS-4 ($17.27) and 43% above GS-6 "
        "($21.54). The efficiency wage premium ($10.37/hr) dominates, driven "
        "primarily by the low detection probability. If <i>q</i> increases to "
        "0.04 (the stated FIA QA rate applied monthly), w* falls to "
        "<b>$22.91/hr</b> \u2014 GS-6 wages ($21.54) fall short by only 6%, and "
        "GS-7 wages ($23.94) exceed the NSC. However, <i>q</i> = 0.04 represents "
        "the <i>stated</i> FIA target rate; the observed effective rate from FIA "
        "DataMart is approximately 0.003 across most states. We computed effective "
        "state-level QA rates as the ratio of blind-check plots (QA_STATUS = 7) to "
        "production plots (QA_STATUS = 1) in the FIA DataMart PLOT table, computed "
        "separately by state and measurement year and averaged across the sample "
        "period. The order-of-magnitude gap between the observed median (~0.3%) and "
        "the stated 4% target reflects both incomplete coverage and the compound "
        "probability structure described above. This sensitivity underscores the "
        "calibration\u2019s central insight: the detection probability <i>q</i> is "
        "the parameter that most strongly governs the incentive gap.",
        S["body_first"]
    ))
    story.append(Paragraph(
        "The magnitude of the NSC gap is also sensitive to the effort cost "
        "assumption: at \u0113 = $2/hr (the lower bound of plausible values), "
        "w* falls to approximately $22/hr, within reach of GS-6. Table 2b "
        "presents the full sensitivity surface. The qualitative conclusion "
        "\u2014 that the NSC exceeds current wages under central and most "
        "alternative parameterizations \u2014 is robust, but specific "
        "percentage gaps should be interpreted as indicative benchmarks, "
        "not precise thresholds.",
        S["body"]
    ))

    add_csv_table(story, TABLE_DIR / "table2_nsc_sensitivity.csv",
                  "Table 2: NSC Critical Wage ($/hr) by Outside Option and Separation Rate",
                  S)

    add_csv_table(story, TABLE_DIR / "table2b_nsc_q_sensitivity.csv",
                  "Table 2b: NSC Sensitivity to Detection Probability (q) and Effort Cost (\u0113)",
                  S)

    add_csv_table(story, TABLE_DIR / "table3_cross_state_nsc.csv",
                  "Table 3: Cross-State NSC Variation Using BLS Wage Data", S)

    add_figure(story, FIG_DIR / "figure1_nsc_sensitivity.png",
               "Figure 1: NSC Sensitivity to Detection Probability (q) and Effort Cost",
               S, width=5.0)

    # ---- 2.5 MULTI-TASK PREDICTIONS AND BEHAVIORAL EXTENSIONS ----
    story.append(Paragraph(
        "2.5 Multi-Task Predictions and Behavioral Extensions", S["h2"]
    ))
    story.append(Paragraph(
        "<b>Multi-task effort allocation.</b> When workers perform multiple tasks "
        "that differ in how easily supervisors can verify them, theory predicts "
        "effort will decline most on the hardest-to-monitor tasks. The binary "
        "effort model treats \u201ccareful measurement\u201d as a single dimension, "
        "but FIA technicians "
        "allocate effort across multiple tasks with different costs and detection "
        "probabilities (Holmstr\u00f6m and Milgrom, 1991). DBH measurement with a "
        "diameter tape is easily verified by QA re-taping; height measurement with "
        "a clinometer requires retreating to find line-of-sight and has inherently "
        "higher inter-observer variance even under honest effort. The multi-task "
        "framework predicts that effort reductions concentrate on the "
        "hardest-to-verify margins \u2014 particularly height estimation. This "
        "prediction is directly testable with the paired data in Section 3.",
        S["body_first"]
    ))
    story.append(Paragraph(
        "<b>Intrinsic motivation.</b> Many FIA technicians have genuine "
        "professional commitment (Perry and Wise, 1990; Buurman et al., 2012). "
        "Following B\u00e9nabou and Tirole (2003, 2006), intrinsic motivation "
        "<i>m</i> effectively reduces the net effort cost to (\u0113 \u2212 "
        "<i>m</i>); when <i>m</i> \u2265 \u0113, the NSC is automatically "
        "satisfied. However, intrinsic motivation faces structural erosion: "
        "seasonal employment undermines professional identity; cumulative fatigue "
        "reduces psychic rewards; and crowding out from monitoring perceived as "
        "distrustful can itself reduce <i>m</i>. Our policy recommendation is "
        "not increased surveillance beyond stated expectations but credible "
        "monitoring at the existing stated rate \u2014 closing the gap between "
        "the stated 4% audit target and the observed effective rate of ~0.3%.",
        S["body"]
    ))
    story.append(Paragraph(
        "<b>Workforce heterogeneity.</b> Career-track seasonals \u2014 GS-0462 "
        "technicians pursuing permanent GS-0460 positions \u2014 treat the "
        "seasonal appointment as a pipeline into federal careers with substantial "
        "employment rents. For these workers, the multi-season career structure "
        "(GS-4\u2192GS-5 after one season, GS-7 upon degree completion) means the "
        "SS framework\u2019s repeated-game logic applies over a multi-year horizon. "
        "Terminal seasonals, by contrast, lack pathways to permanent employment "
        "and face the model\u2019s standard NSC. The calibrated NSC applies to the "
        "marginal (terminal) worker; career-track workers\u2019 tendency to stay "
        "late in the season means late-season crews are positively selected on "
        "effort quality, attenuating seasonal signals.",
        S["body"]
    ))

    # ---- 3. EMPIRICAL ANALYSIS ----
    story.append(Paragraph("3. Empirical Analysis", S["h1"]))
    story.append(Paragraph(
        "The motivating model in Section 2 identifies institutional conditions "
        "under which the no-shirking condition is violated. This section tests the "
        "model\u2019s predictions using paired QA/production measurements from "
        "Yanai et al. (2023), which provide direct evidence of differential "
        "measurement effort across crew types operating under different "
        "institutional incentives. Supplementary forensic analyses \u2014 digit "
        "heaping, allometric residual patterns, and remeasurement growth "
        "anomalies \u2014 largely return null seasonal results, consistent with "
        "the finding below that estimation is pervasive year-round rather than "
        "seasonally concentrated; these are reported in the Supplementary "
        "Materials (Sections A.1\u2013A.7).",
        S["body_first"]
    ))

    story.append(Paragraph("3.1 Data", S["h2"]))
    story.append(Paragraph(
        "We use the paired QA/production dataset from Yanai et al. (2023, "
        "doi:10.2737/RDS-2022-0056), which provides 94,459 paired tree observations "
        "across 24 northern states during 2011\u20132016. Each tree was measured "
        "independently by both a production (field) crew and a QA crew, with "
        "measurements recorded under prefixed field names (F_ for production, "
        "Q_ for QA). The dataset includes HTCD (height method code), recording "
        "whether each height was measured with instruments (HTCD=1), modeled "
        "(HTCD=2), or visually estimated (HTCD=3).",
        S["body_first"]
    ))
    story.append(Paragraph(
        "Sample construction proceeds as follows. Restricting to live trees "
        "present in both visits yields 37,717 paired diameter measurements and "
        "31,568 paired height measurements with valid HTCD codes for both crews. "
        "The geographic distribution is broad: 24 states spanning the Northern, "
        "Northeastern, and North Central FIA regions, with no single state "
        "contributing more than 12% of paired observations. Critically, the "
        "dataset does not include Georgia \u2014 eliminating the geographic "
        "concentration that limits inference in some supplementary analyses "
        "(see Supplementary Materials, Section A.7).",
        S["body"]
    ))
    story.append(Paragraph(
        "Production and QA crews operate under fundamentally different "
        "institutional conditions. Production crews are predominantly seasonal "
        "(term) GS-4/5 employees working under throughput pressure across a full "
        "measurement season. QA crews are typically senior technicians or "
        "supervisory staff performing blind-check remeasurements as part of the "
        "quality assurance program: they have no production quotas, no seasonal "
        "appointment pressure, and an explicit quality mandate. This institutional "
        "contrast provides the identifying variation for the analysis.",
        S["body"]
    ))
    story.append(Paragraph(
        "We define LATE_SEASON as an indicator for months 9\u201312. Regressions "
        "use OLS with standard errors clustered at the state level. Additional "
        "forensic analyses using FIA DataMart data from eight states (4.6 million "
        "tree-observations) are reported in the Supplementary Materials.",
        S["body"]
    ))

    story.append(Paragraph(
        "3.2 Height Method Codes: Direct Evidence of Differential Estimation",
        S["h2"]
    ))

    hdr_style = ParagraphStyle("TH", fontName="TNR-Bold", fontSize=9, leading=11)
    cell_style = ParagraphStyle("TC", fontName="TNR", fontSize=9, leading=11)

    story.append(Paragraph(
        "The headline finding is the differential rate of visual estimation "
        "across crew types. Production crews record HTCD=3 (ocular estimation) "
        "for 23.1% of heights; QA crews record HTCD=3 for only 5.8% \u2014 a "
        "4:1 ratio. This gap is present across species types: for conifers, the "
        "production HTCD=3 rate is 25.9% versus 5.1% for QA; for hardwoods, "
        "22.1% versus 6.0%.",
        S["body_first"]
    ))
    story.append(Paragraph(
        "The cross-tabulation of F_HTCD \u00d7 Q_HTCD reveals a striking "
        "asymmetry. Of the paired observations, 6,402 trees were estimated by "
        "production crews but measured by QA crews, while only 1,010 were "
        "measured by production but estimated by QA \u2014 a 6.3:1 asymmetry in "
        "the direction predicted by the model. The remaining trees were either "
        "measured by both crews or estimated by both, with the latter category "
        "comprising a small fraction of the sample.",
        S["body"]
    ))
    story.append(Paragraph(
        "Not all ocular estimation is unauthorized. FIA protocols permit visual "
        "estimation in specific circumstances. If both production and QA crews "
        "face similar terrain, the <i>differential</i> in HTCD=3 rates (23.1% "
        "vs 5.8%) provides a lower bound on the excess estimation attributable "
        "to institutional differences rather than field conditions. The 4:1 ratio "
        "substantially exceeds what shared terrain conditions alone would produce, "
        "but we cannot determine the exact partition between authorized and "
        "unauthorized estimation from the HTCD codes alone.",
        S["body"]
    ))
    story.append(Paragraph(
        "This differential is not seasonal. A linear probability model of "
        "Prob(F_HTCD=3) on LATE_SEASON with state and year fixed effects yields "
        "a coefficient of \u22120.015 (SE = 0.024, <i>p</i> = 0.54). Production "
        "crews use ocular estimation at roughly the same elevated rate throughout "
        "the measurement season. Decomposing by species type confirms this: neither "
        "conifers (<i>p</i> = 0.22) nor hardwoods (<i>p</i> = 0.58) show a "
        "significant seasonal pattern. Figure 2 displays the HTCD=3 rate by month "
        "with Wilson 95% confidence intervals, confirming the visual impression of "
        "a flat, elevated production estimation rate across all months.",
        S["body"]
    ))
    story.append(Paragraph(
        "The absence of seasonal variation is consistent with structural incentive "
        "misalignment \u2014 if the NSC is violated at current wages throughout the "
        "season, estimation should be pervasive rather than concentrated in late "
        "months. Several alternatives are also consistent with this null: stable "
        "crew composition effects, stable authorized estimation rates, or a "
        "behavioral equilibrium at the observed ~23% rate. The evidentiary weight "
        "rests on the 4:1 production-QA differential, not on the seasonal pattern.",
        S["body"]
    ))
    story.append(Paragraph(
        "State-level variation in HTCD=3 rates provides additional context. While "
        "all states in the sample show higher production than QA estimation rates, "
        "the magnitude varies \u2014 suggesting that local institutional factors "
        "(crew training, supervisory culture, terrain difficulty) modulate the "
        "overall incentive structure. In principle, cross-state variation in "
        "HTCD=3 rates could provide a partial mechanism test \u2014 whether the "
        "estimation differential is larger in states with wider calibrated NSC "
        "gaps (Table 3). However, with only 24 states and strong confounding "
        "between outside wages, terrain difficulty, and forest type, the "
        "statistical power for such a test is limited; we therefore note the "
        "pattern without drawing inferential conclusions.",
        S["body"]
    ))

    add_figure(story, FIG_DIR / "paired_qa_htcd_by_month.png",
               "Figure 2: HTCD=3 (Ocular Estimation) Rates by Measurement Month: "
               "Production vs. QA Crews (Yanai et al. paired dataset).", S)

    story.append(Paragraph(
        "3.3 Corroborating Evidence: The Height-Diameter Asymmetry", S["h2"]
    ))
    story.append(Paragraph(
        "The multi-task model (Section 2.5) predicts that effort reduction "
        "concentrates on the hard-to-verify margin \u2014 height rather than "
        "diameter. The paired data confirm this dramatically.",
        S["body_first"]
    ))
    story.append(Paragraph(
        "<b>Measurement discrepancies.</b> Height discrepancies between production "
        "and QA measurements are substantial: the mean absolute difference is "
        "3.31 feet (SD = 4.91), with a slight negative bias (production heights "
        "average 0.15 feet below QA heights). The distribution is right-skewed, "
        "with a median absolute difference of 2.0 feet and a 90th percentile of "
        "7.0 feet. For diameter, the mean absolute difference is only 0.055 inches "
        "(SD = 0.21), with 95% of pairs agreeing within 0.2 inches \u2014 "
        "confirming that the height margin is dramatically noisier than the "
        "diameter margin. Neither discrepancy shows a significant seasonal pattern "
        "(height: <i>p</i> = 0.64; diameter: <i>p</i> = 0.76).",
        S["body"]
    ))

    add_figure(story, FIG_DIR / "paired_qa_discrepancies.png",
               "Figure 3: Production vs. QA Measurement Discrepancies: "
               "Height (feet) and Diameter (inches).", S)

    story.append(Paragraph(
        "<b>Accuracy by method.</b> Trees where production crews used instruments "
        "(HTCD=1) have mean |HT_diff| = 3.23 feet, while trees where production "
        "crews estimated (HTCD=3) have mean |HT_diff| = 3.48 feet \u2014 estimated "
        "heights are slightly less accurate, though the difference is modest. This "
        "is consistent with estimation introducing some error relative to instrument "
        "measurement while still producing superficially acceptable values.",
        S["body"]
    ))
    story.append(Paragraph(
        "<b>Allometric conformity.</b> We fit an allometric model on QA "
        "measurements as the gold standard (<i>R</i>\u00b2 = 0.71). Trees with "
        "HTCD=1 (measured) have mean |residual| = 0.164 and trees with HTCD=3 "
        "(estimated) have mean |residual| = 0.166 \u2014 effectively identical "
        "(<i>t</i> = \u22120.77, <i>p</i> = 0.44). Estimated and measured "
        "heights show similar deviations from the species-specific "
        "height-diameter relationship, indicating that experienced technicians "
        "who estimate heights do so with sufficient skill that their estimates "
        "are forensically indistinguishable from instrument measurements via "
        "allometric residual analysis. This null is informative for monitoring "
        "design: allometric outlier detection would not identify ocular estimation, "
        "because skilled estimators produce values that conform to the population "
        "allometric relationship.",
        S["body"]
    ))
    story.append(Paragraph(
        "The allometric conformity null also raises a welfare question: if "
        "estimated heights are nearly as accurate as instrument "
        "measurements, the data quality cost of estimation may be more "
        "nuanced than \u201capproximation equals error.\u201d To quantify: "
        "estimated trees (HTCD=3) have mean absolute height discrepancy "
        "of 3.48 ft versus 3.23 ft for measured trees \u2014 a modest 7.7% "
        "accuracy penalty per tree. When propagated through standard volume "
        "equations (volume \u221d height \u00d7 basal area), this translates "
        "to approximately 3\u20134% volume estimation error per tree. While "
        "individually modest, systematic estimation across 23% of "
        "production heights compounds across the inventory and introduces "
        "non-random error correlated with crew institutional conditions. "
        "Three considerations further temper an optimistic reading. First, the "
        "conformity null is a population average \u2014 the tails of the "
        "residual distribution may differ for site-specific applications "
        "(e.g., timber sales on unusual sites where allometric norms are "
        "poor predictors), even if the central tendency is well-preserved. "
        "Second, even if individual estimates are adequate on average, "
        "undetectable estimation erodes the monitoring architecture: when "
        "the QA system cannot distinguish estimated from measured heights, "
        "the equilibrium estimation rate can only increase over time as "
        "workers learn that non-compliance carries no consequences \u2014 "
        "creating a moral hazard spiral. Third, protocol compliance has "
        "independent value because downstream users rely on HTCD codes to "
        "assess data quality; if estimation is forensically invisible, "
        "the HTCD=1 code ceases to be an informative signal.",
        S["body"]
    ))
    story.append(Paragraph(
        "More fundamentally, if skilled estimation is forensically "
        "undetectable through output-based monitoring \u2014 as the "
        "allometric conformity null suggests \u2014 the quality assurance "
        "problem shifts from \u201cdetect bad data\u201d to \u201cverify "
        "process compliance.\u201d This requires input monitoring (GPS "
        "track logging, time-on-plot verification) rather than output "
        "monitoring (allometric outlier detection, QA remeasurement "
        "comparison). The institutional corrosion concern is therefore not "
        "that estimated data are necessarily inaccurate, but that an "
        "output-based QA system is structurally incapable of maintaining "
        "protocol compliance when skilled estimation produces statistically "
        "indistinguishable results. We return to the policy implications "
        "of this distinction in Section 4.",
        S["body"]
    ))
    story.append(Paragraph(
        "<b>Remeasurement anomalies.</b> Corroborating evidence from FIA\u2019s panel "
        "structure confirms the height-diameter asymmetry at scale: across 2,464,859 "
        "remeasurement pairs in eight states, the height anomaly rate is 9.3% "
        "compared to 1.5% for DBH \u2014 a 6:1 ratio. The cleanest seasonal test "
        "\u2014 conifers only, eliminating the leaf-off visibility confound \u2014 "
        "yields a LATE_SEASON coefficient indistinguishable from zero "
        "(<i>p</i> = 0.98), consistent with estimation being pervasive rather "
        "than seasonally concentrated. Full details are in the Supplementary "
        "Materials (Section A.5).",
        S["body"]
    ))

    story.append(Paragraph("3.4 Discussion", S["h2"]))
    story.append(Paragraph(
        "The empirical findings can be stated concisely: production crews "
        "estimate heights at four times the QA rate (23.1% vs. 5.8%), this "
        "differential is pervasive year-round, and effort reduction "
        "concentrates on height rather than diameter \u2014 the measurement "
        "dimension that is both hardest to verify and most time-costly to "
        "perform carefully.",
        S["body_first"]
    ))
    story.append(Paragraph(
        "Multiple mechanisms are consistent with these patterns. The "
        "production-QA differential may reflect incentive misalignment "
        "(the NSC framework in Section 2.4), selection and experience "
        "differences (QA crews are typically GS-7+ supervisory staff), "
        "differential training emphasis, task framing (QA crews know "
        "measurements will be compared), or workload pressure from "
        "production quotas. Clinometer height measurement requires "
        "identifying a sightline, retreating to distance, taking dual "
        "angle readings, and computing \u2014 approximately 2\u20134 minutes "
        "per tree versus 30\u201360 seconds for DBH taping, a roughly 3:1 "
        "time-cost ratio (consistent with the \u0113 micro-foundation in "
        "Section 2.4). A crew under pure throughput pressure would "
        "therefore rationally concentrate time savings on height "
        "independent of any detection-probability calculus. The "
        "height-diameter asymmetry is consistent with both strategic "
        "effort allocation and time-pressure optimization; we cannot "
        "discriminate between these mechanisms from the measurement "
        "data alone.",
        S["body"]
    ))
    story.append(Paragraph(
        "The finite-horizon analysis (Section 2.4) provides a complementary "
        "and possibly more fundamental explanation for the year-round "
        "estimation pattern. For terminal seasonal workers with no prospect "
        "of rehire, backward induction implies the NSC is violated in every "
        "period regardless of wage levels \u2014 estimation is rational "
        "throughout the appointment. This parameter-free prediction is "
        "directly confirmed by the absence of seasonal variation in HTCD=3 "
        "rates, and does not depend on the effort cost calibration.",
        S["body"]
    ))
    story.append(Paragraph(
        "Whether the moral hazard spiral discussed in Section 3.3 has "
        "manifested empirically \u2014 i.e., whether HTCD=3 rates have "
        "trended upward over time \u2014 is an important question that the "
        "current data cannot definitively answer. The paired dataset covers "
        "only six years (2011\u20132016), too short to identify a slow-moving "
        "institutional drift. The FIA DataMart contains HTCD records extending "
        "back to approximately 1999, and was used in this study for supplementary "
        "forensic analyses (Sections A.1\u2013A.7). A systematic temporal trend "
        "analysis of HTCD=3 rates over this longer series was beyond the scope "
        "of the current study but represents a priority for future research.",
        S["body"]
    ))
    story.append(Paragraph(
        "The policy prescription holds regardless of mechanism: whether "
        "production crews estimate more because of weaker incentives, less "
        "experience, time pressure, or some combination, the response is "
        "institutional redesign that narrows the gap between production and "
        "QA measurement conditions \u2014 through enhanced monitoring, "
        "reduced workload pressure, improved training, or career-ladder "
        "investments.",
        S["body"]
    ))
    story.append(Paragraph(
        "The corroborating evidence \u2014 the height-diameter asymmetry "
        "in paired discrepancies, the 6:1 anomaly ratio in remeasurement "
        "data, and the concentration of estimation on the hard-to-verify "
        "measurement dimension \u2014 aligns with the multi-task "
        "prediction about where effort reduction concentrates. The "
        "allometric conformity null indicates that estimation does not "
        "produce detectable forensic signatures through residual analysis, "
        "a finding with direct implications for monitoring system design "
        "(Section 4). Additional forensic analyses \u2014 including digit "
        "heaping, allometric residual patterns, a "
        "difference-in-differences comparison using QA crews as a control "
        "group, and remeasurement growth anomaly analysis across 2.5 "
        "million tree pairs \u2014 are reported in the Supplementary "
        "Materials.",
        S["body"]
    ))
    story.append(Paragraph(
        "Table A1 in the Supplementary Materials systematically catalogs "
        "discriminating predictions across all analyses. Of twelve tests, "
        "the two strongest \u2014 the 4:1 HTCD differential and "
        "height-diameter discrepancy asymmetry \u2014 directly support "
        "differential estimation. The seasonal forensic tests largely "
        "return nulls, consistent with year-round estimation rather than "
        "late-season concentration. Two results \u2014 allometric "
        "conformity (<i>p</i> = 0.44) and late-season variance increase "
        "\u2014 are most difficult to reconcile with a simple estimation "
        "model, suggesting that estimation is performed with sufficient "
        "skill to be forensically undetectable at the population level. "
        "We encourage readers to consult Table A1 for the complete "
        "pattern of evidence.",
        S["body"]
    ))

    # ---- 4. IMPLICATIONS ----
    story.append(Paragraph("4. Implications for Timber Markets and Data Governance", S["h1"]))
    story.append(Paragraph(
        "The paired data provide a nuanced picture of estimation\u2019s consequences: "
        "estimated heights produce allometric residuals statistically "
        "indistinguishable from measured heights (Section 3.3), indicating that "
        "the variance-compression mechanism is not detectable at the population "
        "level. To the extent that estimation reduces the biological information "
        "content of height measurements, its effects on volume estimates would be "
        "non-random: height approximation errors would understate volume for tall "
        "trees and overstate it for short trees, with the net aggregate bias "
        "potentially modest if deviations approximately cancel. The data quality "
        "concern extends beyond systematic volume bias to loss of biological "
        "variance information, attenuation of the HTCD method code signal, and "
        "institutional corrosion of the monitoring architecture.",
        S["body_first"]
    ))
    story.append(Paragraph(
        "The ocular estimation problem is not unique to forest inventory. Analogous "
        "institutional structures \u2014 seasonal or temporary workforces, imperfect "
        "monitoring, hard-to-verify outputs \u2014 arise in fisheries observer "
        "programs, environmental compliance monitoring (Duflo et al., 2013), and "
        "agricultural surveys. The FIA setting is distinctively clean for "
        "calibration: public pay schedules, documented QA rates, and precisely "
        "timed measurement data.",
        S["body"]
    ))
    story.append(Paragraph(
        "More broadly, empirical studies that rely on inventory-derived volume "
        "estimates \u2014 including timber market analyses, carbon accounting models, "
        "and forest growth studies \u2014 could in principle be affected by "
        "systematic measurement error of the type characterized here. Critically, "
        "this error is non-classical: rather than adding noise symmetrically, "
        "ocular estimation compresses height values toward the allometric mean, "
        "attenuating biological variance in ways that standard measurement error "
        "corrections do not address. Characterizing these downstream effects "
        "across specific applications is a natural direction for future work, "
        "though the magnitude in any given study remains to be determined.",
        S["body"]
    ))

    # ---- 5. POLICY ----
    story.append(Paragraph("5. Policy Recommendations", S["h1"]))
    story.append(Paragraph(
        "The calibrated model provides a framework for evaluating specific policy "
        "interventions. These recommendations flow from the institutional analysis, "
        "model calibration, and the empirical finding that production crews estimate "
        "at approximately four times the QA crew rate. We frame these as "
        "implications of the benchmark model, acknowledging that the calibrated "
        "NSC values are indicative rather than precise thresholds.",
        S["body_first"]
    ))
    story.append(Paragraph(
        "At central parameters, the NSC wage ($30.69/hr) far exceeds current "
        "GS-4 ($17.27) and GS-6 ($21.54) wages. Simply raising wages to satisfy "
        "the NSC at current detection probabilities is infeasible within the "
        "General Schedule structure. However, at <i>q</i> = 0.04, w* falls to "
        "$22.91/hr, within reach of GS-7 ($23.94). <b>Increasing effective "
        "monitoring is more cost-effective than raising wages.</b>",
        S["body"]
    ))
    story.append(Paragraph(
        "Specific mechanisms: (1) expand blind-check QA from 4% to 10% of plots "
        "\u2014 the national FIA plot network consists of approximately 130,000 "
        "forested plots, so increasing from 4% to 10% requires approximately "
        "7,800 additional QA plot visits (130,000 \u00d7 0.06), at approximately "
        "17 QA plots per crew-week requiring roughly 450 additional crew-weeks, "
        "at approximately $4,000 per crew-week (two GS-7 technicians at $23.94/hr "
        "plus travel and per diem), or approximately $1.8 million/year nationally; "
        "(2) GPS/accelerometer verification of plot visits at near-zero marginal "
        "cost; (3) automated ML-based consistency checks on incoming data that "
        "increase the subjective detection probability. Institutional reforms "
        "include extended appointments with rehire guarantees (reducing <i>b</i>), "
        "performance feedback loops linking QA results to individual records "
        "(increasing effective <i>q</i>), and career ladders from seasonal GS-4/5 "
        "to permanent GS-7/9 positions. These institutional reforms face "
        "significant headwinds under current federal hiring constraints and "
        "budget pressures, including ongoing reductions in force across USDA "
        "agencies. Finally, remote sensing (e.g., LiDAR-derived tree heights) "
        "may eventually eliminate the human measurement effort margin for the "
        "variable most susceptible to approximation, though ground-based "
        "measurement remains essential for species identification, crown "
        "condition, and other variables that remote sensing cannot reliably "
        "estimate.",
        S["body"]
    ))
    story.append(Paragraph(
        "<b>Feasibility Under Current Federal Constraints.</b> These "
        "recommendations vary substantially in feasibility under current "
        "federal workforce conditions. We sequence them by implementation "
        "difficulty: (1) Technology-assisted monitoring (near-zero marginal "
        "cost) \u2014 most robust to any budget scenario; (2) HTCD-based "
        "auditing (low cost) \u2014 automatable within existing QA infrastructure; "
        "(3) Expanded blind-check QA (~$1.8M/yr) \u2014 moderate cost, requires "
        "sustained appropriations; (4) Career ladders and extended appointments "
        "(highest cost) \u2014 addresses root cause but most vulnerable to hiring "
        "freezes.",
        S["body"]
    ))
    story.append(Paragraph(
        "A potential vicious cycle deserves note: workforce instability "
        "simultaneously causes the data quality problem (by creating conditions "
        "that violate the NSC) and prevents its solution (by constraining the "
        "agency\u2019s capacity to implement reforms). Breaking this cycle requires "
        "recognizing that investment in monitoring infrastructure protects the "
        "downstream value of the data asset.",
        S["body"]
    ))

    # ---- 6. LIMITATIONS ----
    story.append(Paragraph("6. Limitations", S["h1"]))
    story.append(Paragraph(
        "Several limitations of our analysis warrant explicit discussion.",
        S["body_first"]
    ))
    story.append(Paragraph(
        "<b>Geographic and temporal scope of paired data.</b> The paired "
        "QA/production analysis covers 24 northern states during 2011\u20132016. "
        "The absence of southern states means we cannot assess whether the HTCD "
        "differential varies by region, though the consistency across 24 states "
        "suggests a structural rather than regional pattern. The HTCD field "
        "records the crew\u2019s self-reported method code; if crews systematically "
        "underreport estimation, the 23.1% production rate is a lower bound on "
        "actual estimation prevalence.",
        S["body"]
    ))
    story.append(Paragraph(
        "<b>Selection versus incentives in paired comparison.</b> QA and production "
        "crews may differ on dimensions beyond monitoring incentives \u2014 "
        "experience, training intensity, supervisory oversight, workload pressure. "
        "The HTCD differential therefore reflects institutional differences broadly, "
        "not incentive effects in isolation. The policy prescription holds under "
        "multiple mechanisms, but the precise causal channel is not identified.",
        S["body"]
    ))
    story.append(Paragraph(
        "<b>Authorized estimation fraction unknown.</b> FIA protocols permit visual "
        "estimation in specific field conditions. We cannot determine from HTCD "
        "codes what fraction of production crew HTCD=3 records reflects authorized "
        "protocol use versus unauthorized shortcuts. The differential relative to "
        "QA crews provides a lower bound on excess estimation, but the absolute "
        "rate of unauthorized estimation is not identified.",
        S["body"]
    ))
    story.append(Paragraph(
        "<b>Binary effort assumption.</b> The model\u2019s binary effort choice "
        "overstates the discreteness of the actual decision. Calibration results "
        "indicate directional incentive pressures rather than precise wage "
        "thresholds.",
        S["body"]
    ))
    story.append(Paragraph(
        "<b>Effort cost parameterization.</b> The effort cost is grounded in a "
        "time-budget micro-foundation (\u0113/<i>w</i> \u2208 [0.13, 0.36]), but "
        "the wide range reflects substantial terrain and canopy variation. Of the "
        "calibrated parameters, the effort cost has the weakest direct empirical "
        "grounding. Specific NSC percentage gaps (e.g., the 78% and 43% "
        "benchmarks) should be interpreted as indicative of direction and "
        "approximate magnitude rather than precise thresholds. Qualitative "
        "conclusions are robust across this range (Table 2).",
        S["body"]
    ))
    story.append(Paragraph(
        "<b>Crew composition and self-selection.</b> We lack crew-level identifiers "
        "and cannot distinguish within-crew from between-crew composition effects. "
        "Career-track seasonals\u2019 tendency to stay late in the season means the "
        "seasonal signal would be attenuated even if terminal seasonals engage in "
        "estimation.",
        S["body"]
    ))
    story.append(Paragraph(
        "<b>Generalizability.</b> The analysis is specific to the U.S. FIA "
        "program\u2019s institutional design. Other national forest inventories may "
        "face similar or different incentive structures depending on their "
        "workforce model, monitoring intensity, and labor market context.",
        S["body"]
    ))

    # ---- 7. CONCLUSION ----
    story.append(Paragraph("7. Conclusion", S["h1"]))
    conc_paras = [
        "This paper documents differential measurement effort in the Forest "
        "Inventory and Analysis program using paired QA/production data: production "
        "crews record ocular estimation for 23.1% of heights versus 5.8% for QA "
        "crews \u2014 a 4:1 ratio that is pervasive year-round. Height "
        "discrepancies between crew types are dramatic (3.31 ft) while diameter "
        "discrepancies are minimal (0.055 in.), confirming that effort reduction "
        "concentrates on the hard-to-verify measurement margin as multi-task "
        "theory predicts. A supporting efficiency wage calibration shows that "
        "current technician wages fall substantially "
        "below the no-shirking condition under central parameter assumptions "
        "(approximately 78% at GS-4 and 43% at GS-6, though sensitive to the "
        "effort cost parameter), with the detection probability identified as the "
        "dominant parameter.",

        "Three findings deserve emphasis. First, differential estimation is a "
        "structural policy design failure, not a moral failure of individual "
        "technicians. The efficiency wage framework shows that when detection "
        "probabilities are low, seasonal employment offers no career stake, and "
        "outside options are competitive, any rational agent faces incentives to "
        "reduce costly measurement effort. As Section 3 documents, workload "
        "pressure \u2014 the roughly 3:1 time-cost ratio between clinometer height "
        "measurement and DBH taping \u2014 provides an equally viable mechanism; "
        "crucially, both the incentive and workload explanations point toward the "
        "same institutional redesign response. Second, the most cost-effective "
        "intervention is increasing effective detection probability rather than "
        "raising wages: increasing <i>q</i> from 0.01 to 0.04 reduces the NSC "
        "wage from approximately $31/hr to $23/hr under the benchmark "
        "calibration, bringing it within reach of current GS-7 pay grades "
        "($23.94/hr). Third, the HTCD method codes "
        "suggest a concrete monitoring approach: systematic auditing of height "
        "method code distributions across crews and seasons could identify units "
        "with anomalously high estimation rates, enabling targeted intervention "
        "at minimal cost.",

        "The ocular estimation problem extends beyond forest inventory. Any "
        "monitoring program that relies on seasonal or temporary field workers "
        "to collect data under imperfect observation \u2014 fisheries surveys, "
        "agricultural crop assessments, environmental compliance inspections "
        "\u2014 faces analogous incentive structures. The broader implication is "
        "that institutional design matters: monitoring programs that rely primarily "
        "on workers\u2019 intrinsic motivation without aligning extrinsic "
        "incentives are structurally vulnerable to data quality degradation. "
        "While our analysis is specific to the U.S. FIA program, the "
        "institutional structures that create incentives for measurement "
        "approximation \u2014 seasonal workforces, imperfect monitoring, "
        "hard-to-verify outputs \u2014 are common across public data collection "
        "programs worldwide, suggesting that the analytical framework developed "
        "here has broad applicability to monitoring program design.",
    ]
    for i, p in enumerate(conc_paras):
        story.append(Paragraph(p, S["body_first"] if i == 0 else S["body"]))

    # ---- REFERENCES ----
    story.append(PageBreak())
    story.append(Paragraph("References", S["h1"]))

    refs = [
        "Akerlof, George A., and Janet L. Yellen, eds. 1986. <i>Efficiency Wage Models of the Labor Market.</i> Cambridge University Press.",
        "Bechtold, William A., and Paul L. Patterson, eds. 2005. <i>The Enhanced Forest Inventory and Analysis Program.</i> USDA Forest Service GTR SRS-80.",
        "B\u00e9nabou, Roland, and Jean Tirole. 2003. \u201cIntrinsic and Extrinsic Motivation.\u201d <i>Review of Economic Studies</i> 70(3): 489\u2013520.",
        "B\u00e9nabou, Roland, and Jean Tirole. 2006. \u201cIncentives and Prosocial Behavior.\u201d <i>American Economic Review</i> 96(5): 1652\u20131678.",
        "Buurman, Margaretha, et al. 2012. \u201cPublic Sector Employees: Risk Averse and Altruistic?\u201d <i>Journal of Economic Behavior &amp; Organization</i> 83(3): 279\u2013291.",
        "Duflo, Esther, et al. 2013. \u201cTruth-telling by Third-party Auditors.\u201d <i>Quarterly Journal of Economics</i> 128(4): 1499\u20131545.",
        "Frey, Bruno S., and Reto Jegen. 2001. \u201cMotivation Crowding Theory.\u201d <i>Journal of Economic Surveys</i> 15(5): 589\u2013611.",
        "Holmstr\u00f6m, Bengt. 1979. \u201cMoral Hazard and Observability.\u201d <i>Bell Journal of Economics</i> 10(1): 74\u201391.",
        "Holmstr\u00f6m, Bengt, and Paul Milgrom. 1991. \u201cMultitask Principal-Agent Analyses.\u201d <i>Journal of Law, Economics, &amp; Organization</i> 7: 24\u201352.",
        "Mosimann, James E., et al. 2002. \u201cData Fabrication: Can People Generate Random Digits?\u201d <i>Accountability in Research</i> 9(1): 31\u201345.",
        "Nigrini, Mark J. 1996. \u201cA Taxpayer Compliance Application of Benford\u2019s Law.\u201d <i>Journal of the American Taxation Association</i> 18(1): 72\u201391.",
        "Olken, Benjamin A. 2007. \u201cMonitoring Corruption.\u201d <i>Journal of Political Economy</i> 115(2): 200\u2013249.",
        "Perry, James L., and Lois R. Wise. 1990. \u201cThe Motivational Bases of Public Service.\u201d <i>Public Administration Review</i> 50(3): 367\u2013373.",
        "Shapiro, Carl, and Joseph E. Stiglitz. 1984. \u201cEquilibrium Unemployment as a Worker Discipline Device.\u201d <i>American Economic Review</i> 74(3): 433\u2013444.",
        "Simonsohn, Uri. 2013. \u201cJust Post It.\u201d <i>Psychological Science</i> 24(10): 1875\u20131888.",
        "Tomppo, Erkki, et al., eds. 2010. <i>National Forest Inventories.</i> Springer.",
        "USDA Forest Service. 2023. <i>FIA National Core Field Guide, Volume 1.</i> Washington, DC.",
        "Yanai, Ruth D., Alexander R. Young, John L. Campbell, James A. Westfall, Charles J. Barnett, Gretchen A. Dillon, Mark B. Green, and Christopher W. Woodall. 2023. \u201cMeasurement Uncertainty in a National Forest Inventory: Results from the Northern Region of the USA.\u201d <i>Canadian Journal of Forest Research</i> 53(3): 163\u2013177.",
        "Yanai, Ruth D., Alexander R. Young, John L. Campbell, James A. Westfall, Charles J. Barnett, Gretchen A. Dillon, Mark B. Green, and Christopher W. Woodall. 2023. \u201cPaired measurements from quality assurance visits to Forest Inventory and Analysis plots in the northern United States.\u201d Fort Collins, CO: Forest Service Research Data Archive. doi:10.2737/RDS-2022-0056.",
    ]
    for ref in refs:
        story.append(Paragraph(ref, S["ref"]))

    # ---- SUPPLEMENTARY MATERIALS ----
    story.append(PageBreak())
    story.append(Paragraph("Supplementary Materials: Forensic Analyses", S["h1"]))
    story.append(Paragraph(
        "This appendix presents four forensic statistical tests using public FIA "
        "data, a summary table of discriminating predictions, and robustness "
        "analyses. These supplement the paired QA/production comparison in "
        "Section 3 of the main text.",
        S["body_first"]
    ))

    story.append(Paragraph("A.1 FIA DataMart Data", S["h2"]))
    story.append(Paragraph(
        "We use tree-level data from the FIA DataMart for eight states spanning "
        "five FIA regions: Vermont and Maine (Northeast), Minnesota and Wisconsin "
        "(Northern), Georgia (South), Colorado (Rocky Mountain), and Oregon and "
        "Washington (Pacific Northwest). Restricting to production plots "
        "(QA_STATUS = 1) and live trees with valid DBH yields 4,628,494 "
        "tree-observations (1995\u20132025). For the QA comparison, we extract "
        "91,493 additional trees from QA blind-check plots (QA_STATUS = 7). "
        "Georgia contributes the largest QA share (55,345 trees). "
        "LATE_SEASON is defined as in Section 3.1 (indicator for months "
        "9\u201312). All regressions use OLS with standard errors clustered "
        "at the state-year level.",
        S["body_first"]
    ))

    story.append(Paragraph("A.2 Test 1: Digit Heaping", S["h2"]))
    story.append(Paragraph(
        "If technicians approximate DBH, measurements cluster on round numbers. "
        "The overall whole-inch rate is 11.57%, significantly above the 10% "
        "uniform expectation (\u03c7\u00b2 = 41,283, <i>p</i> &lt; 0.001). "
        "However, the seasonal pattern is weak: LATE_SEASON coefficient = 0.0005 "
        "(SE = 0.0003, <i>p</i> = 0.135). Height rounding is also not significant "
        "(<i>p</i> = 0.125). Heaping is concentrated at digits 0 and 1 near the "
        "5.0-inch merchantability threshold, suggesting rounding conventions rather "
        "than seasonal effort variation.",
        S["body_first"]
    ))

    add_figure(story, FIG_DIR / "digit_heaping.png",
               "Figure A1: Digit Heaping by Measurement Month. "
               "(a) Whole-inch DBH rate; (b) Height rounding rate.", S)
    add_figure(story, FIG_DIR / "last_digit_distribution.png",
               "Figure A2: Distribution of DBH Last Digit by Season", S, width=4.0)

    story.append(Paragraph("A.3 Test 2: Allometric Residual Patterns", S["h2"]))
    story.append(Paragraph(
        "If technicians estimate heights from diameter, residuals from "
        "ln(HT) = \u03b2<sub>0</sub> + \u03b2<sub>1</sub> ln(DIA) + \u03b5 will "
        "have <i>lower</i> variance (estimates track the curve). This is opposite "
        "to honest error (fatigue adds noise). We fit the model with species group "
        "FE on production data (<i>N</i> = 4,587,949, <i>R</i>\u00b2 = 0.848). "
        "Levene\u2019s test finds significantly lower late-season variance "
        "(<i>F</i> = 1,642, <i>p</i> &lt; 0.001; SD = 0.219 vs. 0.228). "
        "However, the regression with state and year "
        "FE yields \u03b1<sub>1</sub> \u2248 0 (<i>p</i> = 0.93), suggesting "
        "compositional confounds.",
        S["body_first"]
    ))

    add_figure(story, FIG_DIR / "allometric_residuals.png",
               "Figure A3: Allometric Residual Patterns. (a) Residual SD by month; "
               "(b) Month-specific R\u00b2.", S)

    story.append(Paragraph(
        "A.4 Test 3: QA Crew Comparison (Difference-in-Differences)", S["h2"]
    ))
    story.append(Paragraph(
        "QA crews (QA_STATUS = 7) perform blind remeasurements under fundamentally "
        "different institutional conditions. We estimate: "
        "|\u03b5| = \u03b1<sub>0</sub> + \u03b1<sub>1</sub>\u00b7QA + \u03b1<sub>2</sub>\u00b7LATE "
        "+ \u03b1<sub>3</sub>\u00b7(QA \u00d7 LATE) + state FE + year FE + \u03b7.",
        S["body_first"]
    ))

    # DID results table
    story.append(Paragraph("Table A1: Difference-in-Differences Regression Results",
                           S["table_caption"]))

    did_data = [
        [Paragraph(h, hdr_style) for h in
         ["", "QA", "SE", "LATE", "SE", "QA\u00d7LATE", "<i>p</i>"]],
        [Paragraph(c, cell_style) for c in
         ["(1) |Residual|", "\u22120.0057", "(0.0018)", "0.0001", "(0.0008)",
          "<b>0.0077**</b>", "<b>0.026</b>"]],
        [Paragraph(c, cell_style) for c in
         ["(2) Residual\u00b2", "\u22120.0025", "(0.0011)", "0.0001", "(0.0005)",
          "0.0039*", "0.056"]],
        [Paragraph(c, cell_style) for c in
         ["(3) |Resid|+Spp FE", "\u22120.0045", "(0.0016)", "\u22120.0004", "(0.0008)",
          "<b>0.0067**</b>", "<b>0.045</b>"]],
        [Paragraph(c, cell_style) for c in
         ["(4) DBH Heaping", "\u22120.0001", "(0.0011)", "0.0005", "(0.0003)",
          "0.0021", "0.376"]],
        [Paragraph(c, cell_style) for c in
         ["(5) HT Rounding", "0.0028", "(0.0026)", "\u22120.0019", "(0.0012)",
          "0.0052", "0.270"]],
    ]
    did_table = Table(did_data, colWidths=[1.2*inch, 0.7*inch, 0.7*inch,
                                           0.7*inch, 0.7*inch, 0.9*inch, 0.6*inch])
    did_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, grey),
        ("BACKGROUND", (0, 0), (-1, 0), "#E8E8E8"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(did_table)
    story.append(Paragraph(
        "Notes: <i>N</i> = 4,679,419 (Models 1\u20133, 5) or 4,719,987 (Model 4). "
        "All models include state and year FE. SEs clustered at state-year. "
        "** <i>p</i> &lt; 0.05, * <i>p</i> &lt; 0.10.",
        S["note"]
    ))

    story.append(Paragraph(
        "The DID interaction is positive: \u03b1<sub>3</sub> = 0.0077 "
        "(SE = 0.0035, <i>p</i> = 0.026). However, the wild cluster bootstrap "
        "yields <i>p</i> = 0.403 (Section A.7), indicating this result does not "
        "survive inference appropriate to 8 effective clusters.",
        S["body_first"]
    ))

    add_figure(story, FIG_DIR / "qa_comparison_residuals.png",
               "Figure A4: Allometric Residual Dispersion: Production vs. QA Crews. "
               "(a) Residual SD; (b) Mean |residual|.", S)

    story.append(Paragraph("A.5 Test 4: Remeasurement Growth Anomalies", S["h2"]))
    story.append(Paragraph(
        "Across 2,464,859 remeasurement pairs in eight states, the height anomaly "
        "rate is 9.3% compared to 1.5% for DBH \u2014 a 6:1 ratio. The conifer-only "
        "LATE_SEASON coefficient is effectively zero (<i>p</i> = 0.98). Late-season "
        "height growth variance is higher for both species groups, opposite to the "
        "ocular estimation prediction.",
        S["body_first"]
    ))

    story.append(Paragraph("A.6 Discriminating Predictions", S["h2"]))
    story.append(Paragraph(
        "Table A2: Discriminating Predictions and Results", S["table_caption"]
    ))
    pred_data = [
        [Paragraph(h, hdr_style) for h in
         ["Test", "Ocular Est.", "Honest Error", "Observed"]],
        [Paragraph(c, cell_style) for c in
         ["Digit heaping increases late season", "Yes", "No",
          "Not sig. (<i>p</i> = 0.13)"]],
        [Paragraph(c, cell_style) for c in
         ["Resid. variance decreases late season", "Yes", "No (increases)",
          "Sig. unconditionally"]],
        [Paragraph(c, cell_style) for c in
         ["DID: Prod. suppresses variance increase", "Yes",
          "No", "Conv. <i>p</i>=0.026; bootstrap <i>p</i>=0.403"]],
        [Paragraph(c, cell_style) for c in
         ["HT anomaly rate > DBH (remeas.)", "Yes", "Yes (HT harder)",
          "Yes \u2014 9.3% vs 1.5%"]],
        [Paragraph(c, cell_style) for c in
         ["Conifer HT anomalies increase late", "Yes", "No change",
          "No \u2014 coef \u2248 0, <i>p</i> = 0.98"]],
        [Paragraph(c, cell_style) for c in
         ["<b>Paired: Prod. HTCD=3 > QA</b>", "<b>Yes</b>", "<b>No</b>",
          "<b>Yes \u2014 23.1% vs 5.8% (4:1)</b>"]],
        [Paragraph(c, cell_style) for c in
         ["<b>Paired: HT discrep. > DIA discrep.</b>", "<b>Yes</b>",
          "<b>Yes (HT harder)</b>",
          "<b>Yes \u2014 3.31 ft vs 0.06 in.</b>"]],
    ]
    pred_table = Table(pred_data, colWidths=[1.8*inch, 1.1*inch, 1.2*inch, 2.0*inch])
    pred_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, grey),
        ("BACKGROUND", (0, 0), (-1, 0), "#E8E8E8"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(pred_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("A.7 Robustness", S["h2"]))
    story.append(Paragraph(
        "Table A3: DID Sensitivity by State Grouping", S["table_caption"]
    ))
    sens_data = [
        [Paragraph(h, hdr_style) for h in
         ["Sample", "QA Trees", "\u03b1<sub>3</sub>", "SE", "<i>p</i>"]],
        [Paragraph(c, cell_style) for c in
         ["Full sample (8 states)", "91,493", "<b>0.0077</b>", "0.0035", "<b>0.026</b>"]],
        [Paragraph(c, cell_style) for c in
         ["Georgia only", "55,345", "0.0053", "0.0044", "0.228"]],
        [Paragraph(c, cell_style) for c in
         ["CO + OR + WA", "32,709", "\u22120.0019", "0.0093", "0.838"]],
        [Paragraph(c, cell_style) for c in
         ["All except GA (7 states)", "36,125", "0.0027", "0.0079", "0.729"]],
    ]
    sens_table = Table(sens_data, colWidths=[1.8*inch, 0.9*inch, 0.8*inch, 0.8*inch, 0.8*inch])
    sens_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, grey),
        ("BACKGROUND", (0, 0), (-1, 0), "#E8E8E8"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(sens_table)
    story.append(Paragraph(
        "Notes: All models include state and year FE. "
        "Dependent variable: |allometric residual|.",
        S["note"]
    ))
    story.append(Paragraph(
        "No individual subsample produces a significant interaction. The wild "
        "cluster bootstrap (Cameron et al., 2008) with Rademacher weights at the "
        "state level yields <i>p</i> = 0.403 for the primary DID specification, "
        "reflecting the small effective cluster count (8 states) and Georgia\u2019s "
        "dominance of the QA sample. A Bonferroni correction for the five DID "
        "models would raise the threshold to \u03b1 = 0.01, which the primary "
        "result (<i>p</i> = 0.026) does not meet. The paired analysis in Section 3 "
        "addresses the GA-dominance concern with 24-state coverage.",
        S["body_first"]
    ))

    return story


def main():
    styles = get_styles()
    story = build_story(styles)

    doc = SimpleDocTemplate(
        str(OUT_PATH),
        pagesize=letter,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
        title="Underpaid to Measure?",
        author="Martin Hensley",
    )
    doc.build(story)

    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"Saved: {OUT_PATH}")
    print(f"Size: {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
