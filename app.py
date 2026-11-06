
import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="K-Stock Signal V2",
    page_icon="📈",
    layout="wide"
)

st.title("📈 K-Stock Signal")
st.caption("Korean Stock Market Scanner | V2")

stocks = {
    "Samsung Electronics": "005930.KS",
    "SK Hynix": "000660.KS",
    "NAVER": "035420.KS",
    "Hyundai Motor": "005380.KS",
    "Kia": "000270.KS",
}

@st.cache_data(ttl=900)
def analyze_stock(name, ticker):
    df = yf.Ticker(ticker).history(
        period="1y",
        interval="1d",
        auto_adjust=True
    )

    if df.empty or len(df) < 50:
        return None

    df = df.dropna(subset=["Close"]).copy()

    df["EMA20"] = df["Close"].ewm(
        span=20, adjust=False
    ).mean()

    df["EMA50"] = df["Close"].ewm(
        span=50, adjust=False
    ).mean()

    change = df["Close"].diff()
    gain = change.clip(lower=0)
    loss = -change.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1/14, min_periods=14, adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1/14, min_periods=14, adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(0, float("nan"))
    df["RSI"] = 100 - (100 / (1 + rs))
    df.loc[avg_loss == 0, "RSI"] = 100

    df["AVG_VOLUME"] = df["Volume"].rolling(20).mean()

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    price = float(latest["Close"])
    rsi = float(latest["RSI"])
    ema20 = float(latest["EMA20"])
    ema50 = float(latest["EMA50"])
    volume = float(latest["Volume"])
    avg_volume = float(latest["AVG_VOLUME"])

    if (
        ema20 > ema50
        and rsi > 50
        and volume > avg_volume
    ):
        signal = "BUY"

    elif ema20 < ema50 or rsi < 45:
        signal = "SELL"

    else:
        signal = "HOLD"

    return {
        "Stock": name,
        "Ticker": ticker,
        "Price (KRW)": round(price),
        "Daily Change (%)": round(
            (price / float(previous["Close"]) - 1) * 100, 2
        ),
        "EMA 20": round(ema20),
        "EMA 50": round(ema50),
        "RSI 14": round(rsi, 2),
        "Volume": int(volume),
        "Signal": signal,
        "Data": df
    }

if st.button("🔄 Scan Korean Stocks", type="primary"):
    st.cache_data.clear()

results = []
details = {}

with st.spinner("Scanning stocks..."):
    for name, ticker in stocks.items():
        try:
            result = analyze_stock(name, ticker)
            if result:
                details[name] = result["Data"]
                results.append({
                    key: value
                    for key, value in result.items()
                    if key != "Data"
                })
        except Exception:
            st.warning(f"Could not load {name}.")

if results:
    table = pd.DataFrame(results)

    priority = {"BUY": 0, "HOLD": 1, "SELL": 2}
    table["Priority"] = table["Signal"].map(priority)
    table = table.sort_values(
        ["Priority", "RSI 14"],
        ascending=[True, False]
    )

    st.subheader("Market Scanner")

    buy_count = (table["Signal"] == "BUY").sum()
    hold_count = (table["Signal"] == "HOLD").sum()
    sell_count = (table["Signal"] == "SELL").sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("BUY", int(buy_count))
    c2.metric("HOLD", int(hold_count))
    c3.metric("SELL", int(sell_count))

    st.dataframe(
        table.drop(columns=["Priority"]),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Individual Stock Chart")

    selected = st.selectbox(
        "Choose a stock",
        list(details.keys())
    )

    chart = details[selected]

    st.line_chart(
        chart[["Close", "EMA20", "EMA50"]]
    )

    st.line_chart(chart[["RSI"]])

    st.caption(
        "Signals are technical screening rules, not predictions. "
        "Yahoo Finance data may be delayed, incomplete, or unavailable. "
        "Verify prices with your broker before trading."
    )

else:
    st.info("No stock data available. Try scanning again later.")
