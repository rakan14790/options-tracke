import streamlit as st
import yfinance as yf
import pandas as pd

# إعدادات الصفحة
st.set_page_config(page_title="سلسلة الخيارات - Open Interest Sentiment", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .stDataFrame { border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 تحليل الاهتمام المفتوح والدعم/المقاومة (OI Sentiment)")

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

            # تصحيح الـ Open Interest والـ Volume
            calls['openInterest'] = calls['openInterest'].fillna(0).astype(int)
            puts['openInterest'] = puts['openInterest'].fillna(0).astype(int)

            df = pd.merge(calls, puts, on='strike', suffixes=('_Call', '_Put'), how='outer').sort_values('strike')

            # خوارزمية محسنة لتقييم الـ Long / Short بناءً على المنتصف (Mid-Price) والـ Ask/Bid
            def evaluate_sentiment(last, bid, ask, oi, vol):
                if oi == 0 and vol == 0:
                    return "⚪ خامل"
                
                mid = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else last
                
                # إشارة السيولة العالية
                spike = "🔥 " if (vol > oi and oi > 0) else ""

                if ask > 0 and last >= ask:
                    return spike + "🟢 Long (تجميع Ask)"
                elif bid > 0 and last <= bid:
                    return spike + "🔴 Short (تفريغ Bid)"
                elif last > mid:
                    return spike + "🟢 Long (ميول شرائي)"
                elif last < mid:
                    return spike + "🔴 Short (ميول بيعي)"
                
                return spike + "🟡 محايد"

            df['Call_Sentiment'] = df.apply(lambda r: evaluate_sentiment(r['lastPrice_Call'], r['bid_Call'], r['ask_Call'], r['openInterest_Call'], r['volume_Call']), axis=1)
            df['Put_Sentiment'] = df.apply(lambda r: evaluate_sentiment(r['lastPrice_Put'], r['bid_Put'], r['ask_Put'], r['openInterest_Put'], r['volume_Put']), axis=1)

            st.info(f"📍 **Stock Price ({ticker_symbol}): ${price:g}**")

            # الفلترة حسب عدد السترايكات
            if num_strikes != "ALL":
                df['price_diff'] = (df['strike'] - price).abs()
                df = df.nsmallest(num_strikes, 'price_diff').sort_values('strike')

            df['STRIKE'] = df['strike'].apply(lambda x: f"${int(x)}" if x.is_integer() else f"${x:g}")

            # جدول التنسيق المباشر
            if view_mode == "Calls Only (كول فقط)":
                df_display = pd.DataFrame({
                    'حالة الكول (Flow)': df['Call_Sentiment'],
                    'OI Call': df['openInterest_Call'],
                    'STRIKE': df['STRIKE']
                })
            elif view_mode == "Puts Only (بوت فقط)":
                df_display = pd.DataFrame({
                    'STRIKE': df['STRIKE'],
                    'OI Put': df['openInterest_Put'],
                    'حالة البوت (Flow)': df['Put_Sentiment']
                })
            else:
                df_display = pd.DataFrame({
                    'حالة الكول (Flow)': df['Call_Sentiment'],
                    'OI Call': df['openInterest_Call'],
                    'STRIKE': df['STRIKE'],
                    'OI Put': df['openInterest_Put'],
                    'حالة البوت (Flow)': df['Put_Sentiment']
                })

            st.dataframe(
                df_display,
                use_container_width=True,
                height=750
            )

    except Exception as e:
        st.error(f"حدث خطأ أثناء جلب البيانات: {e}")
