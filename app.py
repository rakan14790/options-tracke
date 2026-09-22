import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="لوحة متابعة عقود الخيارات", layout="wide")
st.title("📈 سعر السهم وعقود الخيارات (Options)")

ticker_symbol = st.sidebar.text_input("أدخل رمز السهم:", value="NVDA").upper()

if ticker_symbol:
    stock = yf.Ticker(ticker_symbol)
    try:
        price = stock.fast_info['lastPrice']
        st.metric(label=f"سعر {ticker_symbol} الحالي", value=f"${price:.2f}")
    except Exception:
        st.error("تأكد من صحة رمز السهم.")
        st.stop()

    expirations = stock.options
    if expirations:
        selected_exp = st.sidebar.selectbox("اختر تاريخ الانتهاء:", expirations)
        opt = stock.option_chain(selected_exp)
        calls, puts = opt.calls, opt.puts
        
        col1, col2 = st.columns(2)
        col1.metric("إجمالي Call Open Interest", f"{int(calls['openInterest'].sum()):,}")
        col2.metric("إجمالي Put Open Interest", f"{int(puts['openInterest'].sum()):,}")

        tab1, tab2 = st.tabs(["🟢 الكول (Calls)", "🔴 البوت (Puts)"])
        cols = ['strike', 'lastPrice', 'bid', 'ask', 'openInterest', 'volume']
        
        with tab1:
            st.dataframe(calls[cols].sort_values(by='strike'), use_container_width=True)
        with tab2:
            st.dataframe(puts[cols].sort_values(by='strike'), use_container_width=True)
