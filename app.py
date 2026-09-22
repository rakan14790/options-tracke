import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import math
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="محلل صانع السوق - Net Gamma & Order Flow", layout="wide")

st.title("🎯 منظومة صانع السوق (Net Gamma, Delta, Order Flow & OI)")

# القائمة الجانبية
st.sidebar.header("⚙️ إعدادات التحليل")
ticker_symbol = st.sidebar.text_input("رمز السهم", value="NVDA").upper()
num_strikes = st.sidebar.select_slider("عدد السترايكات", options=[20, 30, 50, "ALL"], value=30)

# معادلات Black-Scholes المدمجة بدون حزم خارجية
def norm_cdf(x):
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def norm_pdf(x):
    return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)

def calculate_greeks(S, K, T, r, sigma, option_type='call'):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0, 0.0
    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        gamma = norm_pdf(d1) / (S * sigma * math.sqrt(T))
        if option_type == 'call':
            delta = norm_cdf(d1)
        else:
            delta = norm_cdf(d1) - 1.0
        return round(delta, 2), round(gamma, 4)
    except:
        return 0.0, 0.0

if ticker_symbol:
    try:
        stock = yf.Ticker(ticker_symbol)
        price = stock.fast_info['lastPrice']
        
        expirations = stock.options
        if expirations:
            selected_exp = st.selectbox("اختر تاريخ الانتهاء", options=expirations)

            opt = stock.option_chain(selected_exp)
            dt_exp = datetime.strptime(selected_exp, "%Y-%m-%d")
            T = max((dt_exp - datetime.now()).days, 1) / 365.0
            r = 0.045

            calls = opt.calls[['strike', 'lastPrice', 'bid', 'ask', 'openInterest', 'volume', 'impliedVolatility']].copy()
            puts = opt.puts[['strike', 'lastPrice', 'bid', 'ask', 'openInterest', 'volume', 'impliedVolatility']].copy()

            df = pd.merge(calls, puts, on='strike', suffixes=('_Call', '_Put'), how='outer').sort_values('strike').fillna(0)

            call_deltas, call_gammas, put_deltas, put_gammas = [], [], [], []

            for _, row in df.iterrows():
                d_c, g_c = calculate_greeks(price, row['strike'], T, r, row['impliedVolatility_Call'], 'call')
                call_deltas.append(d_c)
                call_gammas.append(g_c)
                
                d_p, g_p = calculate_greeks(price, row['strike'], T, r, row['impliedVolatility_Put'], 'put')
                put_deltas.append(d_p)
                put_gammas.append(g_p)

            df['Call_Delta'] = call_deltas
            df['Call_Gamma'] = call_gammas
            df['Put_Delta'] = put_deltas
            df['Put_Gamma'] = put_gammas

            # حساب Net Gamma & Net Delta الموزونة بالـ Open Interest
            df['Net_Gamma'] = (df['Call_Gamma'] * df['openInterest_Call']) - (df['Put_Gamma'] * df['openInterest_Put'])
            df['Net_Delta'] = (df['Call_Delta'] * df['openInterest_Call']) + (df['Put_Delta'] * df['openInterest_Put'])

            # قراءة الـ Order Flow والسيولة اللحظية (Ask vs Bid)
            def analyze_flow(last, bid, ask, vol, oi):
                if vol == 0:
                    return "⚪ خامل"
                flow_type = ""
                if vol > oi and oi > 0:
                    flow_type = "🔥 Spike "
                
                if ask > bid and last >= ask:
                    return flow_type + "🟢 Long"
                elif ask > bid and last <= bid:
                    return flow_type + "🔴 Short"
                return flow_type + "🟡 محايد"

            df['Call_Flow'] = df.apply(lambda r: analyze_flow(r['lastPrice_Call'], r['bid_Call'], r['ask_Call'], r['volume_Call'], r['openInterest_Call']), axis=1)
            df['Put_Flow'] = df.apply(lambda r: analyze_flow(r['lastPrice_Put'], r['bid_Put'], r['ask_Put'], r['volume_Put'], r['openInterest_Put']), axis=1)

            # ملخص بيئة الجاما الإجمالية
            total_net_gamma = df['Net_Gamma'].sum()
            call_wall_strike = df.loc[df['Call_Gamma'].idxmax()]['strike'] if not df.empty else 0
            put_wall_strike = df.loc[df['Put_Gamma'].idxmax()]['strike'] if not df.empty else 0

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("السعر الحالي", f"${price:g}")
            col2.metric("إجمالي Net Gamma", f"{total_net_gamma:,.2f}", delta="بيئة هادئة (Long Gamma)" if total_net_gamma > 0 else "بيئة متذبذبة (Short Gamma)")
            col3.metric("جدار الكول (Call Wall)", f"${call_wall_strike:g}")
            col4.metric("جدار البوت (Put Wall)", f"${put_wall_strike:g}")

            # الفلترة
            if num_strikes != "ALL":
                df['price_diff'] = (df['strike'] - price).abs()
                df = df.nsmallest(num_strikes, 'price_diff').sort_values('strike')

            df['STRIKE_FORMATTED'] = df['strike'].apply(lambda x: f"{int(x)}" if x.is_integer() else f"{x:g}")

            # جدول العرض النهائي
            df_display = pd.DataFrame({
                'Call Flow': df['Call_Flow'],
                'OI Call': df['openInterest_Call'].astype(int),
                'Delta Call': df['Call_Delta'],
                'Gamma Call': df['Call_Gamma'],
                'Net Gamma الصافية': df['Net_Gamma'].round(2),
                'STRIKE (السترايك)': df['STRIKE_FORMATTED'],
                'Net Delta الصافية': df['Net_Delta'].round(2),
                'Gamma Put': df['Put_Gamma'],
                'Delta Put': df['Put_Delta'],
                'OI Put': df['openInterest_Put'].astype(int),
                'Put Flow': df['Put_Flow']
            })

            st.dataframe(
                df_display.style.background_gradient(subset=['Net Gamma الصافية'], cmap='RdYlGn'),
                use_container_width=True,
                height=700
            )

    except Exception as e:
        st.error(f"حدث خطأ أثناء معالجة البيانات: {e}")
