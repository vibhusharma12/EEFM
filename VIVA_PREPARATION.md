# StockSense AI — College Project Viva & Demonstration Guide

This document is prepared specifically for your college project viva, oral examination, and technical demonstration. It explains every architectural decision and machine learning concept based strictly on the actual codebase.

---

## 1. The 60-Second Elevator Pitch
> *"StockSense AI is a full-stack financial analytics and price forecasting system. It pairs a high-performance React and TypeScript dashboard with a Python FastAPI backend and a scikit-learn machine learning engine. Users can look up international and Indian equities (such as Apple or Reliance), inspect historical quotes across multiple timeframes, and generate 1-day, 7-day, or 30-day price forecasts using a Random Forest Regressor. Rather than predicting raw prices, our model forecasts scale-free relative returns with trailing technical features, strictly avoids look-ahead data leakage via an 80/20 chronological split, benchmark-tests every prediction against a naive persistence baseline, and calculates held-out MAE, RMSE, and R² metrics."*

---

## 2. Problem Statement & Objectives
- **Problem**: Predicting stock prices is challenging due to low signal-to-noise ratios, non-stationarity, and market volatility. Many student projects suffer from three critical flaws:
  1. *Data leakage / look-ahead bias*: Using randomized K-fold cross-validation or future-derived indicators.
  2. *Scale extrapolation failure*: Training tree models on raw dollar prices, which prevents predicting prices higher than historical maximums.
  3. *Illusory accuracy*: Claiming high $R^2$ without testing whether the model beats a simple "tomorrow's price equals today's price" baseline.
- **Objectives**:
  - Deliver an interactive, responsive dashboard for real-time equity exploration.
  - Implement a leak-free ML feature engineering pipeline based purely on backward-looking data.
  - Benchmark Random Forest predictions against a naive baseline on an untouched chronological hold-out window.
  - Recursively generate multi-step forecasts with transparent assumptions for unobservable future inputs.

---

## 3. Technology Stack Selection Rationale
| Layer | Choice | Why It Was Chosen |
| :--- | :--- | :--- |
| **Frontend** | React 19 + TypeScript + Vite | Type safety prevents UI runtime crashes; Vite provides sub-second HMR and optimized production bundles; Recharts enables responsive financial charting. |
| **Backend** | FastAPI + Uvicorn (Python 3.12) | Asynchronous, lightweight, high-performance web framework with native Pydantic v2 data validation and automatic OpenAPI documentation. |
| **ML Engine** | scikit-learn + NumPy + Pandas | Industry standard for tabular regression; `RandomForestRegressor` provides non-linear modeling and variance reduction via bagging without the extreme overfitting risk of deep neural networks on small datasets. |
| **Data Provider** | yfinance | Free, reliable access to global historical daily OHLCV bars without requiring paid API keys. |
| **Persistence** | Joblib | High-efficiency binary serialization of trained scikit-learn estimators and metadata. |

---

## 4. How Yahoo Finance Data Is Retrieved & Managed
- Handled in `backend/app/market.py`.
- Requests pass ticker symbol and period (e.g. `AAPL`, `5y`) to `yf.Ticker(symbol).history()`.
- **Validation & Cleaning**:
  - Tickers are validated against a strict regex (`/^[A-Z0-9][A-Z0-9.\-^=]{0,14}$/`).
  - Missing days and duplicate date indices are dropped.
  - Raw closes are preserved matching exchange settlement prices.
- **Resilience & Caching**:
  - Thread-safe in-memory cache stores successful responses for 300 seconds (5 minutes) to prevent Yahoo Finance HTTP 429 rate limits.
  - Ticker-not-found (404) errors are cached for 60 seconds.
  - Upstream network errors and rate limits return clean HTTP 502/429 status codes with user-friendly messages rather than Python stack traces.

---

## 5. Feature Engineering: Formulae & Alignment
All features are generated in `backend/app/ml/features.py`. For every session $t$, **only data known at or before the close of session $t$ is used**:

1. **Relative Lagged Closes**:
   $$\text{close\_lag\_k\_rel} = \frac{\text{Close}_{t-k}}{\text{Close}_t} - 1 \quad \text{for } k \in \{1, 2, 3, 5, 10\}$$
2. **Daily Returns & Lagged Returns**:
   $$\text{ret\_1} = \frac{\text{Close}_t}{\text{Close}_{t-1}} - 1, \quad \text{ret\_lag\_k} = \text{ret\_1}(t-k) \quad \text{for } k \in \{1, 2, 3, 5\}$$
3. **Distance to Moving Averages**:
   $$\text{dist\_sma\_w} = \frac{\text{Close}_t}{\text{SMA}_w(t)} - 1 \quad \text{where } \text{SMA}_w(t) = \frac{1}{w}\sum_{i=0}^{w-1} \text{Close}_{t-i} \quad \text{for } w \in \{5, 10, 20, 50\}$$
4. **Rolling Volatility**:
   $$\text{volatility\_w} = \text{std}(\text{daily returns over trailing } w \text{ sessions}) \quad \text{for } w \in \{5, 10, 20\}$$
5. **Intraday Price Range**:
   $$\text{range\_pct} = \frac{\text{High}_t - \text{Low}_t}{\text{Close}_t}$$
6. **Volume Change**:
   $$\text{volume\_chg} = \text{clip}\left(\frac{\text{Volume}_t}{\text{Volume}_{t-1}} - 1, -0.9, 3.0\right)$$

### Target Alignment:
$$\text{Target}_t = \frac{\text{Close}_{t+1}}{\text{Close}_t} - 1$$
Constructed with `close.shift(-1)`. Row $t$ contains features known at session $t$ and predicts the relative move to session $t+1$. The final observed session has no target and is never used in training; it is the seed for future forecasting.

---

## 6. How Random Forest Regression Works
- Handled in `backend/app/ml/model.py`.
- **Ensemble Method**: Fits an ensemble of 150 regression trees (`n_estimators=150`).
- **Bootstrap Aggregation (Bagging)**: Each tree is trained on a random bootstrap sample (sampling with replacement) of the training dataset.
- **Feature Subsampling**: At each split, each tree only considers a random subset of features ($\sqrt{p}$), decorrelating the individual trees.
- **Variance Reduction**: Individual decision trees have high variance and easily overfit noise. Averaging predictions across 150 diverse trees reduces variance without increasing bias:
  $$\widehat{y} = \frac{1}{150} \sum_{m=1}^{150} T_m(x)$$
- **Extrapolation Safety**: Because the forest predicts relative return $\Delta P / P$ instead of raw price $P$, it is scale-invariant and does not cap predictions at historical price ceilings.

---

## 7. Why We Use a Chronological Train/Test Split
- Standard machine learning libraries offer `train_test_split(shuffle=True)`. **Shuffling time-series observations is a fatal flaw**:
  - If Monday and Wednesday are in the training set and Tuesday is in the test set, Tuesday’s price is interpolated from adjacent known points.
  - This causes **look-ahead bias / target leakage**, generating artificially high test scores ($R^2 > 0.98$) that fail completely in real forward testing.
- **Our Approach**: We split strictly by time: the first 80% of sessions are the training set; the final 20% are held out as the test set. The model is fitted only on the earlier data.

---

## 8. What MAE, RMSE, and R² Mean
- **MAE (Mean Absolute Error)**:
  $$\text{MAE} = \frac{1}{N}\sum_{i=1}^N |y_i - \widehat{y}_i|$$
  Measures average prediction error directly in the currency of the stock (e.g. `$3.16` on Apple). Easy to interpret.
- **RMSE (Root Mean Squared Error)**:
  $$\text{RMSE} = \sqrt{\frac{1}{N}\sum_{i=1}^N (y_i - \widehat{y}_i)^2}$$
  Squares individual errors before averaging, penalizing large outlier errors heavily.
- **$R^2$ Score (Coefficient of Determination)**:
  $$R^2 = 1 - \frac{\sum (y_i - \widehat{y}_i)^2}{\sum (y_i - \bar{y})^2}$$
  Measures the proportion of target variance explained by the model relative to simply predicting the mean.
  *Important Note*: If a model performs worse than predicting the historical average, $R^2$ is **negative**. StockSense displays negative $R^2$ truthfully without clamping to zero.

---

## 9. Why a Naive Baseline Is Necessary
- Under the **Efficient Market Hypothesis**, stock price movements closely follow a random walk (martingale property):
  $$E[P_{t+1} \mid P_t] \approx P_t$$
- The simplest baseline is **naive persistence**: predict that tomorrow’s price will equal today’s price ($\widehat{P}_{t+1} = P_t$).
- Because stock prices are autocorrelated, naive persistence achieves low MAE and high raw correlation.
- **A machine learning model only has genuine predictive value if its test MAE is lower than this naive baseline**. If our model has a higher MAE than the baseline, StockSense honestly reports `beatBaselineMae: false`.

---

## 10. How Recursive Multi-Step Forecasting Works
- Handled in `backend/app/ml/forecasting.py`.
- We use a one-step-ahead model to forecast $H \in \{1, 7, 30\}$ trading sessions:
  1. Compute features using known history up to session $t$.
  2. Predict relative return and compute $\widehat{P}_{t+1} = P_t \times (1 + \widehat{\text{ret}})$.
  3. Append $\widehat{P}_{t+1}$ to the working history series.
  4. Recompute all lagged prices, moving averages, and volatility features using the updated series.
  5. Repeat the process to predict $\widehat{P}_{t+2}, \dots, \widehat{P}_{t+H}$.
- **Handling Unobservable Future OHLCV**:
  - Future High, Low, and Volume cannot be observed.
  - Rather than making false claims, the system uses transparent, documented approximations: future high-low range is set to the recent 20-session average, and future volume change is assumed to be 0.
- **Future Trading Dates**: Generated with `pandas.bdate_range()`, automatically skipping Saturdays and Sundays.

---

## 11. Why 30-Day Forecasts Are Less Reliable Than 1-Day Forecasts
1. **Compounding Feedback Loops**: In recursive forecasting, step 2 uses step 1's prediction; step 30 uses 29 successive synthetic predictions. Any initial prediction error compounds exponentially over time.
2. **Missing External Catalysts**: Over 30 trading days (~6 calendar weeks), real market prices are driven by quarterly earnings reports, macroeconomic interest rate decisions, inflation data, and geopolitical news—none of which are present in trailing technical price tables.
3. **Mean Reversion of Tree Regressors**: Without new trend shocks, recursive tree predictions tend to flatten towards the conditional average of the training distribution.

---

## 12. Honest Limitations of the System
- **No Fundamental or Sentiment Data**: The model does not ingest news sentiment, social media, SEC 10-K filings, or order book liquidity.
- **Exchange Holidays**: The date generator skips weekends, but does not model local exchange bank holidays (e.g., Diwali on NSE or Thanksgiving on NASDAQ).
- **Not Financial Advice**: Stock price forecasting is inherently stochastic; past statistical patterns do not guarantee future profitability.

---

## 13. Top 5 Likely Examiner Questions & Recommended Answers

### Q1: "Why did you choose Random Forest instead of an LSTM or GRU recurrent neural network?"
> **Answer**: *"LSTMs are powerful for sequence modeling, but on single-asset daily financial time series they frequently overfit because stock data has a very low signal-to-noise ratio and relatively small sample sizes (~1,200 trading days in 5 years). LSTMs also require extensive hyperparameter tuning and lack direct feature interpretability. Random Forest uses bagging to directly reduce model variance, trains in seconds on CPU, provides clear feature importances via MDI, and does not require complex sequence normalization."*

### Q2: "What is look-ahead bias, and how did your implementation prevent it?"
> **Answer**: *"Look-ahead bias, or data leakage, happens when information from the future is inadvertently included in the training features. We prevented it in two ways: first, all rolling windows (moving averages, volatility, lags) are strictly backward-looking. Second, we enforced a strict chronological 80/20 train/test split. The model is trained solely on data up to the split point; the test period is completely untouched during training."*

### Q3: "Why did you predict relative percentage return instead of the raw stock price?"
> **Answer**: *"Decision trees partition the feature space into orthogonal rectangles and predict constant leaf values. As a result, a tree regressor cannot extrapolate outside the range of values in its training set. If a stock is trading at an all-time high of $200, a model trained on past prices between $100 and $180 could never predict $205. By predicting relative return $(\Delta P / P)$, our target is stationary and scale-invariant, allowing the model to project growth at any price level."*

### Q4: "What does it mean if your Random Forest has an R² of 0.95, but higher MAE than the naive baseline?"
> **Answer**: *"In price space, high R² can be misleading because stock prices are strongly autocorrelated—today's price is already very close to yesterday's price. The true test of financial predictive power is whether the model's Mean Absolute Error improves upon the naive baseline $(\widehat{P}_{t+1} = P_t)$. If the model's MAE is worse than the baseline, the model is simply adding noise to persistence, which is why our dashboard transparently displays whether the model actually beat the baseline."*

### Q5: "How does your system handle Indian stocks listed on the National Stock Exchange (NSE)?"
> **Answer**: *"Our symbol normalizer supports Yahoo Finance conventions, specifically the `.NS` suffix for National Stock Exchange tickers (e.g. `RELIANCE.NS`, `TCS.NS`, `INFY.NS`). The frontend automatically formats values in Indian Rupees (₹), and the backend uses the same scale-free feature pipeline to train and forecast."*
