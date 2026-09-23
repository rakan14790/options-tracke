import streamlit as st
import yfinance as yf
import pandas as pd

# إعدادات الصفحة
st.set_page_config(page_title="سلسلة الخيارات - Webull Style", layout="wide")

# تصميم علوي وألوان شبيهة بـ Webull
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .stDataFrame { border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 سلسلة الخيارات (Options Chain)")

# القائمة الجانبية
st.sidebar.header("⚙️ إعدادات العرض")
ticker_symbol = st.sidebar.text_input("رمز السهم", value="NVDA").upper()

view_mode = st.sidebar.radio(
    "عرض العقود:",
    options=["Both (الكول والبوت)", "Calls Only (كول فقط)", "Puts Only (بوت فقط)"]
)

num_strikes = st.sidebar.select_slider("عدد السترايكات", options=[20, 30, 50, "ALL"], value=30)

if ticker_symbol:
    try:
        stock = yf.Ticker(ticker_symbol)
        price = stock.fast_info['lastPrice']
        
        expirations = stock.options
        if expirations:
            selected_exp = st.selectbox("اختر تاريخ الانتهاء", options=expirations)

            opt = stock.option_chain(selected_exp)

            calls = opt.calls[['strike', 'lastPrice', 'bid', 'ask', 'openInterest', 'volume']].copy()
            puts = opt.puts[['strike', 'lastPrice', 'bid', 'ask', 'openInterest', 'volume']].copy()

            # معالجة الـ Open Interest والـ Volume لمنع ظهور الأصفار الوهمية
            calls['openInterest'] = calls['openInterest'].fillna(0).astype(int)
            puts['openInterest'] = puts['openInterest'].fillna(0).astype(int)
            calls['volume'] = calls['volume'].fillna(0).astype(int)
            puts['volume'] = puts['volume'].fillna(0).astype(int)

            df = pd.merge(calls, puts, on='strike', suffixes=('_Call', '_Put'), how='outer').sort_values('strike')

            # تحليل الاتجاه (Long / Short / Spike)
            def analyze_flow(last, bid, ask, vol, oi):
                if vol == 0 and oi == 0:
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

            # شريط السعر الحالي بتنسيق Webull
            st.info(f"📍 **Stock Price ({ticker_symbol}): ${price:g}**")

            # الفلترة حسب عدد السترايكات القريبة من السعر
            if num_strikes != "ALL":
                df['price_diff'] = (df['strike'] - price).abs()
                df = df.nsmallest(num_strikes, 'price_diff').sort_values('strike')

            df['STRIKE'] = df['strike'].apply(lambda x: f"${int(x)}" if x.is_integer() else f"${x:g}")

            # بناء الواجهة بحسب نمط Webull (الكول يسار | السترايك منتصف | البوت يمين)
            if view_mode == "Calls Only (كول فقط)":
                df_display = pd.DataFrame({
                    'Flow (Calls)': df['Call_Flow'],
                    'Volume (Call)': df['volume_Call'],
                    'Open Int (Call)': df['openInterest_Call'],
                    'STRIKE': df['STRIKE']
                })
            elif view_mode == "Puts Only (بوت فقط)":
                df_display = pd.DataFrame({
                    'STRIKE': df['STRIKE'],
                    'Open Int (Put)': df['openInterest_Put'],
                    'Volume (Put)': df['volume_Put'],
                    'Flow (Puts)': df['Put_Flow']
                })
            else: # Both (التنسيق المطابق لـ Webull)
                df_display = pd.DataFrame({
                    'Flow (Call)': df['Call_Flow'],
                    'Vol (Call)': df['volume_Call'],
                    'Open Int (Call)': df['openInterest_Call'],
                    'STRIKE': df['STRIKE'],
                    'Open Int (Put)': df['openInterest_Put'],
                    'Vol (Put)': df['volume_Put'],
                    'Flow (Put)': df['Put_Flow']
                })

            st.dataframe(
                df_display,
                use_container_width=True,
                height=700
            )

    except Exception as e:
        st.error(f"حدث خطأ أثناء جلب البيانات: {e}")
