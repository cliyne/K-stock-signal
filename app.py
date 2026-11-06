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
st.caption("Korean Stock Market Analysis Dashboard")

stocks = {
    "Samsung Electronics": "005930.KS",
    "SK Hynix": "000660.KS",
    "NAVER": "035420.KS",
    "Hyundai Motor": "005380.KS",
    "Kia": "000270.KS",
}

selected_stock = st.selectbox(
    "Choose a Korean stock",
    list(stocks.keys())
)

ticker = stocks[selected_stock]

@st.cache_data(ttl=900)
def get_stock_data(symbol):
    data = yf.Ticker(symbol).history(
        period="1y",
        interval="1d",
        auto_adjust=True
    )
    return data

with st.spinner("Loading stock data..."):
    try:
        df = get_stock_data(ticker)

        if df.empty or len(df) < 50:
            st.error("Not enough stock data available.")
            st.stop()

        df = df.dropna(subset=["Close"]).copy()

        # Moving averages
        df["EMA20"] = df["Close"].ewm(
            span=20, adjust=False
        ).mean()

        df["EMA50"] = df["Close"].ewm(
            span=50, adjust=False
        ).mean()

        # RSI 14
        change = df["Close"].diff()
        gains = change.clip(lower=0)
        losses = -change.clip(upper=0)

        avg_gain = gains.ewm(
            alpha=1/14, min_periods=14, adjust=False
        ).mean()

        avg_loss = losses.ewm(
            alpha=1/14, min_periods=14, adjust=False
        ).mean()

        rs = avg_gain / avg_loss.replace(0, float("nan"))
        df["RSI14"] = 100 - (100 / (1 + rs))
        df.loc[avg_loss == 0, "RSI14"] = 100

        # Average volume
        df["VolumeAvg20"] = df["Volume"].rolling(20).mean()

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        price = float(latest["Close"])
        change_pct = (
            (price / float(previous["Close"])) - 1
        ) * 100

        rsi = float(latest["RSI14"])
        volume = float(latest["Volume"])
        average_volume = float(latest["VolumeAvg20"])

        # Simple educational signal rules
        if (
            latest["EMA20"] > latest["EMA50"]
            and rsi > 50
            and volume > average_volume
        ):
            signal = "BUY"
            explanation = "Uptrend, positive momentum and above-average volume."

        elif latest["EMA20"] < latest["EMA50"] or rsi < 45:
            signal = "SELL"
            explanation = "Trend or momentum is weakening."

        else:
            signal = "HOLD"
            explanation = "The current conditions do not confirm a BUY setup."

        # Dashboard
        st.subheader(selected_stock)

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Latest Price",
            f"₩{price:,.0f}",
            f"{change_pct:+.2f}%"
        )

        col2.metric(
            "RSI (14)",
            f"{rsi:.1f}"
        )

        col3.metric(
            "EMA 20",
            f"₩{latest['EMA20']:,.0f}"
        )

        col4.metric(
            "EMA 50",
            f"₩{latest['EMA50']:,.0f}"
        )

        st.divider()

        st.subheader("Trading Signal")

        if signal == "BUY":
            st.success("🟢 BUY")
        elif signal == "SELL":
            st.error("🔴 SELL")
        else:
            st.info("🟡 HOLD")

        st.write(explanation)

        st.caption(
            f"Latest volume: {volume:,.0f} shares | "
            f"20-day average: {average_volume:,.0f} shares"
        )

        # Candlestick chart
        st.subheader("Price Chart")

        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Stock Price"
        ))

        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["EMA20"],
            name="EMA 20",
            line=dict(color="orange", width=2)
        ))

        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["EMA50"],
            name="EMA 50",
            line=dict(color="blue", width=2)
        ))

        fig.update_layout(
            height=550,
            xaxis_rangeslider_visible=False,
            template="plotly_dark"
        )

        st.plotly_chart(fig, use_container_width=True)

        # RSI chart
        st.subheader("RSI Indicator")

        rsi_fig = go.Figure()

        rsi_fig.add_trace(go.Scatter(
            x=df.index,
            y=df["RSI14"],
            name="RSI 14",
            line=dict(color="purple")
        ))

        rsi_fig.add_hline(y=70, line_dash="dash")
        rsi_fig.add_hline(y=30, line_dash="dash")

        rsi_fig.update_layout(
            height=250,
            yaxis_range=[0, 100],
            template="plotly_dark"
        )

        st.plotly_chart(rsi_fig, use_container_width=True)

        st.caption(
            "Data source: Yahoo Finance via yfinance. "
            "Quotes may be delayed or unavailable. "
            "Signals are educational indicators, not guaranteed predictions."
        )

    except Exception as e:
        st.error("Unable to load stock data right now.")
        st.caption(f"Technical details: {e}")