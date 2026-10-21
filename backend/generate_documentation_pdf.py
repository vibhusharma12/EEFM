"""Generate the comprehensive StockSense AI Technical Documentation PDF."""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.pdfgen import canvas

PDF_OUTPUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "StockSense_AI_Documentation.pdf"))


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and display total page counts and running headers."""

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
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, total_pages):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#5c6478"))

        # Suppress header on cover/first page
        if self._pageNumber > 1:
            self.drawString(45, 752, "StockSense AI — Technical Architecture & ML Specification")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(45, 746, 567, 746)

        # Running Footer on all pages
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(45, 42, 567, 42)
        self.drawString(45, 30, "StockSense AI · College Final Year Project · Academic Documentation")
        self.drawRightString(567, 30, f"Page {self._pageNumber} of {total_pages}")
        self.restoreState()


def build_pdf():
    # 45pt margins for a clean 3-page layout
    doc = SimpleDocTemplate(
        PDF_OUTPUT_PATH,
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=45,
        bottomMargin=45,
    )

    styles = getSampleStyleSheet()

    # Palette
    c_primary = colors.HexColor("#0f172a")    # Slate 900
    c_accent = colors.HexColor("#1d4ed8")     # Blue 700
    c_subtext = colors.HexColor("#334155")    # Slate 700
    c_border = colors.HexColor("#cbd5e1")     # Slate 300
    c_bg_alt = colors.HexColor("#f8fafc")     # Slate 50

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=c_primary,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=c_subtext,
        spaceAfter=10,
    )
    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=c_accent,
        spaceBefore=8,
        spaceAfter=5,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=c_primary,
        spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3,
    )
    callout_style = ParagraphStyle(
        "Callout",
        parent=body_style,
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#1e293b"),
    )
    th_style = ParagraphStyle(
        "TH",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )
    td_style = ParagraphStyle(
        "TD",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=c_primary,
    )
    td_code = ParagraphStyle(
        "TDCode",
        parent=td_style,
        fontName="Courier",
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # Title Block
    story.append(Paragraph("StockSense AI", title_style))
    story.append(Paragraph("Technical Specification, Machine Learning Architecture &amp; Data Flow Guide", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.2, color=c_accent, spaceBefore=0, spaceAfter=8))

    # Executive Overview
    story.append(Paragraph("Project Overview", h1_style))
    story.append(Paragraph(
        "StockSense AI is an end-to-end financial intelligence and price forecasting system. It connects a reactive, "
        "type-safe <b>React 19 + TypeScript + Vite</b> dashboard to an asynchronous <b>FastAPI</b> Python service. "
        "The system downloads historical global market bars, transforms them into non-linear, scale-free technical indicators, "
        "and fits an ensemble <b>RandomForestRegressor</b> using a strictly chronological hold-out window. "
        "Predicted trajectories are benchmarked against a naive persistence baseline and recursively projected forward "
        "for 1, 7, and 30 trading sessions.",
        body_style,
    ))

    # Section 1: How Data Is Fetched
    story.append(Paragraph("1. Data Acquisition &amp; Ingestion: How Market Data Is Fetched", h1_style))
    story.append(Paragraph(
        "Market data is streamed dynamically from <b>Yahoo Finance</b> via the Python <code>yfinance</code> library "
        "within <code>backend/app/market.py</code>. The application is completely dynamic and does not rely on static "
        "CSV files or hardcoded prices.",
        body_style,
    ))
    story.append(Paragraph("• <b>Ticker Symbol Validation:</b> All incoming queries are validated against the regex <code>^[A-Z0-9][A-Z0-9.\\-^=]{0,14}$</code>. Malformed or SQL-injection style inputs are rejected immediately with HTTP 400 before reaching the network layer.", bullet_style))
    story.append(Paragraph("• <b>Global &amp; Indian Market Coverage:</b> The system seamlessly supports US exchanges (NASDAQ, NYSE) and Indian equities via National Stock Exchange suffixes (e.g., <code>RELIANCE.NS</code>, <code>TCS.NS</code>, <code>INFY.NS</code>). The frontend automatically binds appropriate currency symbols ($, INR).", bullet_style))
    story.append(Paragraph("• <b>Historical Lookback Horizons:</b> Requests pull daily bars across 5 allowable periods: <code>1mo</code>, <code>3mo</code>, <code>6mo</code>, <code>1y</code>, and <code>5y</code>. For machine learning training, a 5-year lookback (~1,250 trading days) is loaded to guarantee adequate samples for moving average warm-up and testing.", bullet_style))
    story.append(Paragraph("• <b>Data Hygiene &amp; Sanitization:</b> Raw quotes are cleaned: duplicate timestamps are dropped keeping the latest session, non-trading weekend gaps are parsed natively, rows missing Close prices are dropped, and invalid negative/infinite prices are filtered out.", bullet_style))
    story.append(Paragraph("• <b>Error Mapping Without Stack Traces:</b> Upstream timeouts, delisted symbols, and Yahoo rate limits are intercepted and mapped into client-safe exceptions (<code>TickerNotFound</code> &rarr; 404, <code>RateLimited</code> &rarr; 429, <code>UpstreamUnavailable</code> &rarr; 502), ensuring internal server internals are never exposed.", bullet_style))

    # Section 2: How Data Is Stored
    story.append(Paragraph("2. Storage Architecture: Why No Database (Supabase / SQL) Is Used", h1_style))
    story.append(Paragraph(
        "A common question during technical review is why external databases like Supabase, PostgreSQL, or MongoDB "
        "were intentionally omitted from the architecture. The design uses lightweight, high-performance local persistence "
        "tailored for machine learning inference:",
        body_style,
    ))

    storage_table_data = [
        [
            Paragraph("Storage Layer", th_style),
            Paragraph("Implementation", th_style),
            Paragraph("Technical Purpose &amp; Advantages", th_style),
        ],
        [
            Paragraph("<b>In-Memory Quote Cache</b>", td_style),
            Paragraph("<code>market.py</code><br/>Thread-safe dictionary with monotonic clock TTL", td_code),
            Paragraph("Caches live quotes for 300 seconds (5 min). Prevents Yahoo Finance rate-limiting (HTTP 429) during repeated user clicks. Invalid tickers (404) are cached for 60s.", td_style),
        ],
        [
            Paragraph("<b>Model Persistence</b>", td_style),
            Paragraph("<code>joblib.dump()</code><br/><code>backend/models/*.joblib</code>", td_code),
            Paragraph("Trained Random Forest estimators and evaluation metadata are serialized as binary files on disk. Subsequent predictions load from disk in &lt;10ms, eliminating redundant retraining.", td_style),
        ],
        [
            Paragraph("<b>Why No SQL / Supabase?</b>", td_style),
            Paragraph("Stateless REST Design", td_code),
            Paragraph("1. Market data is already hosted and indexed globally by Yahoo Finance; duplicating price tables in SQL adds latency and maintenance overhead.<br/>2. There are no user accounts, passwords, or transactional states to store.<br/>3. Loading numpy matrices from Joblib binaries is significantly faster than parsing rows from an external database over network sockets.", td_style),
        ],
    ]
    st_table = Table(storage_table_data, colWidths=[110, 130, 282])
    st_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), c_accent),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, c_border),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, c_bg_alt]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(st_table)
    story.append(Spacer(1, 6))

    # Section 3: Feature Engineering
    story.append(Paragraph("3. Feature Engineering: Formulae &amp; Zero Look-Ahead Bias", h1_style))
    story.append(Paragraph(
        "All features are implemented in <code>backend/app/ml/features.py</code>. A fundamental constraint is that "
        "for any session <i>t</i>, <b>only prices and volumes occurring at or before session <i>t</i> can be used</b>. "
        "Future data never leaks into features.",
        body_style,
    ))

    feat_table_data = [
        [
            Paragraph("Feature Name", th_style),
            Paragraph("Mathematical Definition", th_style),
            Paragraph("Economic / Technical Purpose", th_style),
        ],
        [
            Paragraph("<code>close_lag_k_rel</code>", td_code),
            Paragraph("(Close<sub>t-k</sub> / Close<sub>t</sub>) - 1<br/>for k &isin; {1, 2, 3, 5, 10}", td_style),
            Paragraph("Captures short-to-medium momentum and price distance from prior sessions without unit dependence.", td_style),
        ],
        [
            Paragraph("<code>ret_1</code> &amp; <code>ret_lag_k</code>", td_code),
            Paragraph("ret<sub>t</sub> = (Close<sub>t</sub> / Close<sub>t-1</sub>) - 1<br/>Lagged: k &isin; {1, 2, 3, 5}", td_style),
            Paragraph("Measures immediate velocity and autocorrelation of daily percentage price changes.", td_style),
        ],
        [
            Paragraph("<code>dist_sma_w</code>", td_code),
            Paragraph("(Close<sub>t</sub> / SMA<sub>w</sub>(t)) - 1<br/>for w &isin; {5, 10, 20, 50}", td_style),
            Paragraph("Quantifies trend extension: distance of current close from trailing 1-week, 2-week, 1-month, and 10-week moving averages.", td_style),
        ],
        [
            Paragraph("<code>volatility_w</code>", td_code),
            Paragraph("std(ret<sub>t-w..t</sub>)<br/>for w &isin; {5, 10, 20}", td_style),
            Paragraph("Captures market turbulence and regime shifts across 5, 10, and 20 trading sessions.", td_style),
        ],
        [
            Paragraph("<code>range_pct</code>", td_code),
            Paragraph("(High<sub>t</sub> - Low<sub>t</sub>) / Close<sub>t</sub>", td_style),
            Paragraph("Measures session price dispersion and intraday volatility.", td_style),
        ],
        [
            Paragraph("<code>volume_chg</code>", td_code),
            Paragraph("clip((Vol<sub>t</sub> / Vol<sub>t-1</sub>) - 1, -0.9, 3.0)", td_style),
            Paragraph("Identifies institutional accumulation or distribution spikes, clipped to tame non-stationary anomalies.", td_style),
        ],
    ]
    ft_table = Table(feat_table_data, colWidths=[100, 140, 282])
    ft_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), c_accent),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, c_border),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, c_bg_alt]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(ft_table)
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "<b>Target Alignment (Shift -1):</b> The target variable is the next session's percentage return: "
        "<code>Target<sub>t</sub> = (Close<sub>t+1</sub> / Close<sub>t</sub>) - 1</code>. "
        "Because 50-day Simple Moving Average requires 50 historical closes, the earliest 49 warm-up rows are discarded. "
        "The very last session has no target and is held out to seed future forecasts.",
        callout_style,
    ))

    # Section 4: Machine Learning Algorithm
    story.append(Paragraph("4. Machine Learning Implementation: Random Forest Regressor", h1_style))
    story.append(Paragraph(
        "The algorithm is implemented in <code>backend/app/ml/model.py</code> using <code>scikit-learn</code>.",
        body_style,
    ))
    story.append(Paragraph("• <b>Why Random Forest?</b> Stock price dynamics contain non-linear interactions (e.g. crossing a moving average while volatility spikes). Linear models fail to capture these without manual combinatorial features. Recurrent networks (LSTMs) frequently overfit noisy daily stock data. Random Forest uses bootstrap aggregation (bagging) to average 150 diverse trees, dramatically curtailing variance without inflating bias.", bullet_style))
    story.append(Paragraph("• <b>Stationary Relative Returns:</b> Decision trees partition feature space into piecewise constant regions and <i>cannot extrapolate outside their training range</i>. Training on raw prices would artificially cap predictions at all-time highs. Training on scale-free returns (change / price) resolves this fundamental limitation.", bullet_style))
    story.append(Paragraph("• <b>Chronological 80/20 Train-Test Split:</b> Time-series observations are never randomly shuffled. Shuffling leaks future price information into training. The earlier 80% forms the training window; the latest 20% forms the untouched test set.", bullet_style))
    story.append(Paragraph("• <b>Naive Baseline Benchmarking:</b> In financial economics, asset prices approximate a martingale (E[P<sub>t+1</sub> | P<sub>t</sub>] &approx; P<sub>t</sub>). StockSense benchmarks Random Forest against the naive persistence baseline (predicted P<sub>t+1</sub> = P<sub>t</sub>). If the Random Forest fails to beat the baseline MAE, it reports that result honestly.", bullet_style))

    # Section 5: Recursive Forecasting
    story.append(Paragraph("5. Recursive Multi-Step Forecasting Engine", h1_style))
    story.append(Paragraph(
        "In <code>backend/app/ml/forecasting.py</code>, multi-step forecasts (1, 7, and 30 trading sessions) are generated "
        "recursively using the one-step-ahead trained model:",
        body_style,
    ))
    story.append(Paragraph("1. <b>Step Execution:</b> At step <i>k</i>, compute technical features from the working history and predict relative price return.", bullet_style))
    story.append(Paragraph("2. <b>Dynamic History Update:</b> Compute predicted close P<sub>t+k</sub> = P<sub>t+k-1</sub> &times; (1 + return) and append the predicted price to the working close series.", bullet_style))
    story.append(Paragraph("3. <b>Recalculate Trailing Windows:</b> Recompute lags, moving averages, and rolling volatilities incorporating the newly predicted close. Features are never held static.", bullet_style))
    story.append(Paragraph("4. <b>Transparent Unobservable Assumptions:</b> Because future High, Low, and Volume cannot be observed, the model holds future high-low range at the recent 20-session average and assumes volume change is 0. Future dates skip Saturdays and Sundays.", bullet_style))
    story.append(Paragraph("5. <b>Error Compounding:</b> 30-day forecasts are inherently less certain than 1-day forecasts because step 30 relies on 29 successive synthetic inputs. This limitation is explicitly communicated in the UI.", bullet_style))

    # Section 6: Full Parameter Master Reference
    story.append(Paragraph("6. Master Parameter Reference Table", h1_style))

    param_table_data = [
        [
            Paragraph("Category", th_style),
            Paragraph("Parameter Name", th_style),
            Paragraph("Default Value", th_style),
            Paragraph("Architectural &amp; Mathematical Role", th_style),
        ],
        [
            Paragraph("<b>Model Hyperparameters</b>", td_style),
            Paragraph("<code>n_estimators</code>", td_code),
            Paragraph("150", td_style),
            Paragraph("Number of independent decision trees in the ensemble. Provides variance reduction through bagging.", td_style),
        ],
        [
            Paragraph("<b>Model Hyperparameters</b>", td_style),
            Paragraph("<code>max_depth</code>", td_code),
            Paragraph("10", td_style),
            Paragraph("Maximum depth of each tree. Prevents trees from memorizing localized market noise.", td_style),
        ],
        [
            Paragraph("<b>Model Hyperparameters</b>", td_style),
            Paragraph("<code>min_samples_leaf</code>", td_code),
            Paragraph("2", td_style),
            Paragraph("Minimum samples required in terminal leaf nodes, preventing single-outlier splits.", td_style),
        ],
        [
            Paragraph("<b>Model Hyperparameters</b>", td_style),
            Paragraph("<code>random_state</code>", td_code),
            Paragraph("42", td_style),
            Paragraph("Guarantees deterministic, reproducible tree splits and bagging bootstrap samples.", td_style),
        ],
        [
            Paragraph("<b>Model Hyperparameters</b>", td_style),
            Paragraph("<code>n_jobs</code>", td_code),
            Paragraph("-1", td_style),
            Paragraph("Utilizes all available CPU cores for parallel tree fitting.", td_style),
        ],
        [
            Paragraph("<b>Dataset &amp; Split</b>", td_style),
            Paragraph("<code>TRAIN_FRACTION</code>", td_code),
            Paragraph("0.80 (80%)", td_style),
            Paragraph("Chronological partition ratio: earliest 80% train, subsequent 20% held-out test.", td_style),
        ],
        [
            Paragraph("<b>Dataset &amp; Split</b>", td_style),
            Paragraph("<code>MIN_TRAIN_SAMPLES</code>", td_code),
            Paragraph("60 sessions", td_style),
            Paragraph("Minimum required training rows; throws HTTP 422 if history is insufficient.", td_style),
        ],
        [
            Paragraph("<b>Dataset &amp; Split</b>", td_style),
            Paragraph("<code>MIN_TEST_SAMPLES</code>", td_code),
            Paragraph("20 sessions", td_style),
            Paragraph("Minimum hold-out test rows to ensure evaluation metric validity.", td_style),
        ],
        [
            Paragraph("<b>Technical Windows</b>", td_style),
            Paragraph("<code>LAG_PERIODS</code>", td_code),
            Paragraph("1, 2, 3, 5, 10", td_style),
            Paragraph("Trading day intervals for lagged relative close features.", td_style),
        ],
        [
            Paragraph("<b>Technical Windows</b>", td_style),
            Paragraph("<code>SMA_WINDOWS</code>", td_code),
            Paragraph("5, 10, 20, 50", td_style),
            Paragraph("Trailing sessions for Simple Moving Average distances.", td_style),
        ],
        [
            Paragraph("<b>Technical Windows</b>", td_style),
            Paragraph("<code>VOL_WINDOWS</code>", td_code),
            Paragraph("5, 10, 20", td_style),
            Paragraph("Rolling window sizes for standard deviation of percentage returns.", td_style),
        ],
        [
            Paragraph("<b>Runtime Config</b>", td_style),
            Paragraph("<code>CACHE_TTL_SECONDS</code>", td_code),
            Paragraph("300 (5 min)", td_style),
            Paragraph("In-memory cache lifetime for successful Yahoo Finance queries.", td_style),
        ],
        [
            Paragraph("<b>Runtime Config</b>", td_style),
            Paragraph("<code>UPSTREAM_TIMEOUT</code>", td_code),
            Paragraph("10 seconds", td_style),
            Paragraph("Timeout limit for external Yahoo Finance HTTP requests before raising HTTP 504.", td_style),
        ],
        [
            Paragraph("<b>Runtime Config</b>", td_style),
            Paragraph("<code>PERSIST_MODELS</code>", td_code),
            Paragraph("true", td_style),
            Paragraph("Enables automatic serialization of trained models to <code>backend/models/</code>.", td_style),
        ],
        [
            Paragraph("<b>API Routing</b>", td_style),
            Paragraph("<code>horizon</code>", td_code),
            Paragraph("1 to 30", td_style),
            Paragraph("Allowable forward forecast sessions validated via FastAPI Query/Body constraints.", td_style),
        ],
    ]
    pt_table = Table(param_table_data, colWidths=[95, 105, 75, 247])
    pt_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), c_accent),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, c_border),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, c_bg_alt]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(pt_table)
    story.append(Spacer(1, 8))

    # Concluding Disclaimer
    story.append(Paragraph(
        "<b>Academic Disclaimer:</b> Predictions generated by StockSense AI are statistical projections based on "
        "historical price patterns and technical market indicators. They are intended strictly for academic demonstration "
        "and research in computational finance and do not constitute financial advice.",
        callout_style,
    ))

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully built: {PDF_OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
