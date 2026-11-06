
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="K-Stock Signal",
    page_icon="📈",
    layout="wide"
)

st.title("📈 K-Stock Signal")
st.caption("Korean Stock Market Scanner | Version 3")

st.info(
    "Technical analysis tool for Korean stocks. "
    "Signals are indicators, not guaranteed predictions."
)

# Korean stock watchlist
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

    if df.empty or len(df) < 60:
        return None

    df = df.dropna(subset=["Close"]).copy()

    # Moving averages
    df["EMA20"] = df["Close"].ewm(
        span=20,
        adjust=False
    ).mean()

    df["EMA50"] = df["Close"].ewm(
        span=50,
        adjust=False
    ).mean()

    # RSI 14
    change = df["Close"].diff()
    gain = change.clip(lower=0)
    loss = -change.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1/14,
        min_periods=14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1/14,
        min_periods=14,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(0, float("nan"))

    df["RSI"] = 100 - (100 / (1 + rs))
    df.loc[avg_loss == 0, "RSI"] = 100

    # Volume
    df["AVG_VOLUME"] = df["Volume"].rolling(20).mean()

    # Signal conditions
    buy_condition = (
        (df["EMA20"] > df["EMA50"]) &
        (df["RSI"] > 50) &
        (df["Volume"] > df["AVG_VOLUME"])
    )

    sell_condition = (
        (df["EMA20"] < df["EMA50"]) |
        (df["RSI"] < 45)
    )

    df["BUY_MARKER"] = df["Close"].where(buy_condition)

    df["SELL_MARKER"] = df["Close"].where(
        sell_condition & ~buy_condition
    )

    # Avoid using an unfinished current-day candle:
    # use the latest completed daily candle available.
    df = df.dropna(subset=["EMA20", "EMA50", "RSI", "AVG_VOLUME"])

    if len(df) < 2:
        return None

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    price = float(latest["Close"])
    ema20 = float(latest["EMA20"])
    ema50 = float(latest["EMA50"])
    rsi = float(latest["RSI"])
    volume = float(latest["Volume"])
    avg_volume = float(latest["AVG_VOLUME"])

    # Latest signal
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

    # Illustrative risk levels, not trade instructions
    entry = price
    stop_loss = price * 0.97
    take_profit = price * 1.06

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
        "Entry Estimate": round(entry),
        "Stop Loss": round(stop_loss),
        "Take Profit": round(take_profit),
        "Data": df
    }


# Scan button
if st.button("🔄 Scan Korean Stocks", type="primary"):
    st.cache_data.clear()

results = []
details = {}

with st.spinner("Analyzing Korean stocks..."):

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

        except Exception as e:
            st.warning(f"Could not load {name}: {e}")


if results:

    table = pd.DataFrame(results)

    priority = {
        "BUY": 0,
        "HOLD": 1,
        "SELL": 2
    }

    table["Priority"] = table["Signal"].map(priority)

    table = table.sort_values(
        ["Priority", "RSI 14"],
        ascending=[True, False]
    )

    # Summary
    st.subheader("Market Overview")

    buy_count = (table["Signal"] == "BUY").sum()
    hold_count = (table["Signal"] == "HOLD").sum()
    sell_count = (table["Signal"] == "SELL").sum()

    c1, c2, c3 = st.columns(3)

    c1.metric("BUY Signals", int(buy_count))
    c2.metric("HOLD Signals", int(hold_count))
    c3.metric("SELL Signals", int(sell_count))

    # Scanner table
    st.subheader("Stock Scanner")

    st.dataframe(
        table.drop(columns=["Priority"]),
        use_container_width=True,
        hide_index=True
    )

    # Individual stock chart
    st.subheader("BUY / SELL Chart")

    selected = st.selectbox(
        "Choose a stock",
        list(details.keys())
    )

    chart = details[selected]

    fig = go.Figure()

    # Price
    fig.add_trace(go.Scatter(
        x=chart.index,
        y=chart["Close"],
        name="Stock Price",
        line=dict(color="blue", width=2)
    ))

    # EMA 20
    fig.add_trace(go.Scatter(
        x=chart.index,
        y=chart["EMA20"],
        name="EMA 20",
        line=dict(color="orange")
    ))

    # EMA 50
    fig.add_trace(go.Scatter(
        x=chart.index,
        y=chart["EMA50"],
        name="EMA 50",
        line=dict(color="purple")
    ))

    # BUY markers
    fig.add_trace(go.Scatter(
        x=chart.index,
        y=chart["BUY_MARKER"],
        mode="markers",
        name="BUY",
        marker=dict(
            color="green",
            size=12,
            symbol="triangle-up"
        )
    ))

    # SELL markers
    fig.add_trace(go.Scatter(
        x=chart.index,
        y=chart["SELL_MARKER"],
        mode="markers",
        name="SELL",
        marker=dict(
            color="red",
            size=12,
            symbol="triangle-down"
        )
    ))

    fig.update_layout(
        title=f"{selected} - Trading Signals",
        xaxis_title="Date",
        yaxis_title="Price (KRW)",
        height=600,
        hovermode="x unified",
        legend_title="Indicators"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # RSI chart
    st.subheader("RSI 14")

    rsi_fig = go.Figure()

    rsi_fig.add_trace(go.Scatter(
        x=chart.index,
        y=chart["RSI"],
        name="RSI",
        line=dict(color="blue")
    ))

    rsi_fig.add_hline(
        y=70,
        line_dash="dash",
        line_color="red",
        annotation_text="Overbought 70"
    )

    rsi_fig.add_hline(
        y=30,
        line_dash="dash",
        line_color="green",
        annotation_text="Oversold 30"
    )

    rsi_fig.update_layout(
        title="Relative Strength Index",
        yaxis_range=[0, 100],
        height=350
    )

    st.plotly_chart(
        rsi_fig,
        use_container_width=True
    )

    # Volume chart
    st.subheader("Trading Volume")

    volume_fig = go.Figure()

    volume_fig.add_trace(go.Bar(
        x=chart.index,
        y=chart["Volume"],
        name="Volume"
    ))

    volume_fig.add_trace(go.Scatter(
        x=chart.index,
        y=chart["AVG_VOLUME"],
        name="20-Day Average Volume"
    ))

    volume_fig.update_layout(
        title="Volume Analysis",
        height=350
    )

    st.plotly_chart(
        volume_fig,
        use_container_width=True
    )

    # Risk information
    st.subheader("Risk Level Estimates")

    selected_row = table[table["Stock"] == selected].iloc[0]

    r1, r2, r3 = st.columns(3)

    r1.metric(
        "Reference Price",
        f"₩{selected_row['Entry Estimate']:,}"
    )

    r2.metric(
        "Illustrative Stop Loss",
        f"₩{selected_row['Stop Loss']:,}"
    )

    r3.metric(
        "Illustrative Take Profit",
        f"₩{selected_row['Take Profit']:,}"
    )

    st.caption(
        "Stop loss and take profit are illustrative percentage levels "
        "of the latest price, not optimized trading levels."
    )

    st.caption(
        "Data source: Yahoo Finance via yfinance. "
        "Quotes may be delayed, incomplete, or unavailable. "
        "The latest daily candle may not be a live quote. "
        "Verify all prices with your broker before trading."
    )

else:

    st.warning(
        "No stock data available. Try again later."
    )

    st.caption(
        "The market may be closed or the data provider may be unavailable."
    )
