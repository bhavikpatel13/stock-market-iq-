"""
╔══════════════════════════════════════════════════════════════════╗
║         STOCK MARKET INTELLIGENCE DASHBOARD                      ║
║         Production-Ready | Python + Streamlit + Plotly           ║
╚══════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
from src.data_fetcher import DataFetcher
from src.indicators import TechnicalIndicators
from src.charts import ChartBuilder
from src.config import WATCHLIST, PAGE_CONFIG, PERIODS

# ─── Page Config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(**PAGE_CONFIG)

# ─── Inject Custom CSS ────────────────────────────────────────────────────────
with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">📊 StockIQ</div>', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-sub">Market Intelligence Dashboard</p>', unsafe_allow_html=True)
    st.divider()

    # Stock selector
    st.markdown("**Select Stock**")
    ticker_label = st.selectbox(
        "Ticker",
        options=list(WATCHLIST.keys()),
        label_visibility="collapsed"
    )
    symbol = WATCHLIST[ticker_label]

    # Period selector
    st.markdown("**Time Period**")
    period_label = st.select_slider(
        "Period",
        options=list(PERIODS.keys()),
        value="3 Months",
        label_visibility="collapsed"
    )
    days = PERIODS[period_label]

    # Chart type
    st.markdown("**Chart Type**")
    chart_type = st.radio(
        "Chart Type",
        ["Candlestick", "Line", "OHLC Bar"],
        label_visibility="collapsed",
        horizontal=False
    )

    st.divider()
    st.markdown("**Overlays**")
    show_ma     = st.toggle("Moving Averages (MA20/MA50)", value=True)
    show_bb     = st.toggle("Bollinger Bands", value=True)
    show_vwap   = st.toggle("VWAP", value=False)

    st.divider()
    st.markdown("**Sub-Charts**")
    show_volume = st.toggle("Volume", value=True)
    show_rsi    = st.toggle("RSI (14)", value=True)
    show_macd   = st.toggle("MACD", value=True)

    st.divider()
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()

    st.caption("Data via Yahoo Finance · Updates on refresh")

# ─── Fetch Data ───────────────────────────────────────────────────────────────
fetcher = DataFetcher()

with st.spinner(f"Loading {ticker_label}..."):
    df, meta = fetcher.get_stock_data(symbol, days)

if df is None or df.empty:
    st.error(f"⚠️ Could not load data for **{symbol}**. Check your internet connection and try again.")
    st.stop()

# Add technical indicators
df = TechnicalIndicators.add_all(df)

# ─── Header Row ───────────────────────────────────────────────────────────────
latest  = df["Close"].iloc[-1]
prev    = df["Close"].iloc[-2]
change  = latest - prev
pct     = (change / prev) * 100
high52  = df["High"].max()
low52   = df["Low"].min()
rsi_val = df["RSI"].iloc[-1]
vol_avg = df["Volume"].mean()
mkt_cap = meta.get("marketCap", 0)

arrow   = "▲" if change >= 0 else "▼"
clr_cls = "positive" if change >= 0 else "negative"

st.markdown(f"""
<div class="header-block">
    <div class="ticker-name">{ticker_label}</div>
    <div class="ticker-symbol">{symbol}</div>
    <div class="price-row">
        <span class="price">${latest:,.2f}</span>
        <span class="change {clr_cls}">{arrow} {abs(change):.2f} ({abs(pct):.2f}%)</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Metric Cards ─────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)
cards = [
    (c1, "52W High",   f"${high52:,.2f}",   None),
    (c2, "52W Low",    f"${low52:,.2f}",    None),
    (c3, "RSI (14)",   f"{rsi_val:.1f}",    "Overbought" if rsi_val > 70 else ("Oversold" if rsi_val < 30 else "Neutral")),
    (c4, "Avg Volume", f"{vol_avg/1e6:.2f}M", None),
    (c5, "Day High",   f"${df['High'].iloc[-1]:,.2f}", None),
    (c6, "Mkt Cap",    f"${mkt_cap/1e9:.1f}B" if mkt_cap else "N/A", None),
]
for col, label, val, note in cards:
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{val}</div>
        {"<div class='metric-note'>"+note+"</div>" if note else ""}
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Main Price Chart ─────────────────────────────────────────────────────────
builder = ChartBuilder(df, symbol, ticker_label)
price_fig = builder.price_chart(
    chart_type=chart_type,
    show_ma=show_ma,
    show_bb=show_bb,
    show_vwap=show_vwap
)
st.plotly_chart(price_fig, use_container_width=True, config={"displayModeBar": True, "scrollZoom": True})

# ─── Sub-charts ───────────────────────────────────────────────────────────────
active_sub = [s for s, flag in [("Volume", show_volume), ("RSI", show_rsi), ("MACD", show_macd)] if flag]
if active_sub:
    cols = st.columns(len(active_sub))
    for col, sub in zip(cols, active_sub):
        with col:
            if sub == "Volume":
                st.plotly_chart(builder.volume_chart(), use_container_width=True)
            elif sub == "RSI":
                st.plotly_chart(builder.rsi_chart(), use_container_width=True)
            elif sub == "MACD":
                st.plotly_chart(builder.macd_chart(), use_container_width=True)

# ─── Data Table + Statistics ──────────────────────────────────────────────────
st.divider()
tab1, tab2, tab3 = st.tabs(["📋 Recent Data", "📐 Statistics", "📥 Export"])

with tab1:
    display = df[["Open","High","Low","Close","Volume"]].tail(15).copy()
    display.index = display.index.strftime("%Y-%m-%d")
    display["Change%"] = display["Close"].pct_change().mul(100).round(2)
    display = display.round(2)
    display["Volume"] = display["Volume"].apply(lambda x: f"{int(x):,}")
    st.dataframe(display, use_container_width=True)

with tab2:
    s = df["Close"]
    import numpy as np
    stats = {
        "Mean Price":     f"${s.mean():.2f}",
        "Std Deviation":  f"${s.std():.2f}",
        "Variance":       f"{s.var():.2f}",
        "Skewness":       f"{s.skew():.4f}",
        "Kurtosis":       f"{s.kurtosis():.4f}",
        "Daily Return μ": f"{s.pct_change().mean()*100:.3f}%",
        "Daily Return σ": f"{s.pct_change().std()*100:.3f}%",
        "Sharpe Ratio":   f"{(s.pct_change().mean()/s.pct_change().std()*np.sqrt(252)):.3f}",
        "Max Drawdown":   f"{((s/s.cummax()-1).min()*100):.2f}%",
    }
    import pandas as pd
    stats_df = pd.DataFrame(stats.items(), columns=["Metric", "Value"]).set_index("Metric")
    st.dataframe(stats_df, use_container_width=True)

with tab3:
    csv = df.to_csv().encode("utf-8")
    st.download_button(
        "⬇️ Download CSV",
        data=csv,
        file_name=f"{symbol}_{period_label.replace(' ','_')}.csv",
        mime="text/csv",
        use_container_width=True
    )
    st.caption(f"Exports last {len(df)} trading days of OHLCV + indicator data for **{symbol}**")

st.markdown('<p class="footer">⚠️ For educational purposes only · Not financial advice · Data via Yahoo Finance</p>', unsafe_allow_html=True)