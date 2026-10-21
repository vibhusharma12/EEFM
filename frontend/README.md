# StockSense AI Frontend

React 19 + TypeScript + Vite dashboard for real-time stock analysis and machine learning forecasting.

## Features
- **Stock Overview**: Recent quotes, daily change %, intraday range, volume, and company profile.
- **Historical Chart**: Interactive price and volume charts across 1M, 3M, 6M, 1Y, and 5Y horizons.
- **Machine Learning Forecasting**:
  - Configurable 1, 7, and 30 trading-day forecast horizons.
  - Interactive Recharts visualization with clear boundary marking where forecast begins.
  - Actual vs. predicted closing price overlay.
- **Model Evaluation Panel**:
  - Test-set MAE, RMSE, and $R^2$ (with full support for negative $R^2$).
  - Naive baseline benchmark comparison.
  - Transparent sample counts and training/test date ranges.
- **Model Explanation & Feature Importance**:
  - In-depth explanation of Random Forest, feature construction, chronological split, and evaluation.
  - Dynamic feature importance chart derived from the scikit-learn model.
  - Mandatory financial disclaimer.

## Running Locally

```bash
npm install
npm run dev
```

Dashboard runs at `http://localhost:5173`.
To build for production:
```bash
npm run build
```
