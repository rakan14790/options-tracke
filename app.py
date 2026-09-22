import streamlit as st
import yfinance as yf
import pandas as pd

# إعدادات الصفحة
st.set_page_config(page_title="محلل التدفق والسيولة - Order Flow & OI", layout="wide")

st.title("🎯 منظومة تتبع سيولة وتدفق الأوبشن (Order Flow & OI Analysis)")

# القائمة الجانبية
st.sidebar.header("⚙️ إعدادات التحليل")
ticker_symbol = st.sidebar.text_input("رمز السهم", value="NVDA").upper()
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

            df = pd.merge(calls, puts, on='strike', suffixes=('_Call', '_Put'), how='outer').sort_values('strike').fillna(0)

            # تحديد نوع التدفق (Long / Short / Spike)
            def analyze_flow(last, bid, ask, vol, oi):
                if vol == 0:
                    return "⚪ خامل"
                
                flow_type = ""
                # كشف الدخول السريع (Vol أكبر من OI)
                if vol > oi and oi > 0:
                    flow_type = "🔥 Spike "
                
                # التمييز بين الشراء (Long) والبيع (Short)
                if ask > bid and last >= ask:
                    return flow_type + "🟢 Long"
                elif ask > bid and last <= bid:
                    return flow_type + "🔴 Short"
                
                return flow_type + "🟡 محايد"

            df['Call_Flow'] = df.apply(lambda r: analyze_flow(r['lastPrice_Call'], r['bid_Call'], r['ask_Call'], r['volume_Call'], r['openInterest_Call']), axis=1)
            df['Put_Flow'] = df.apply(lambda r: analyze_flow(r['lastPrice_Put'], r['bid_Put'], r['ask_Put'], r['volume_Put'], r['openInterest_Put']), axis=1)

            # عرض سعر السهم الحالي
            st.metric("السعر الحالي للسهم", f"${price:g}")
            st.markdown("---")

            # الفلترة حسب عدد السترايكات القريبة من السعر
            if num_strikes != "ALL":
                df['price_diff'] = (df['strike'] - price).abs()
                df = df.nsmallest(num_strikes, 'price_diff').sort_values('strike')

            df['STRIKE_FORMATTED'] = df['strike'].apply(lambda x: f"{int(x)}" if x.is_integer() else f"{x:g}")

            # الجدول التفاعلي القديم المباشر
            df_display = pd.DataFrame({
                'Call Flow': df['Call_Flow'],
                'OI Call': df['openInterest_Call'].astype(int),
                'Vol Call': df['volume_Call'].astype(int),
                'Last Call': df['lastPrice_Call'],
                'STRIKE (السترايك)': df['STRIKE_FORMATTED'],
                'Last Put': df['lastPrice_Put'],
                'Vol Put': df['volume_Put'].astype(int),
                'OI Put': df['openInterest_Put'].astype(int),
                'Put Flow': df['Put_Flow']
            })

            st.dataframe(
                df_display,
                use_container_width=True,
                height=750
            )

    except Exception as e:
        st.error(f"حدث خطأ أثناء جلب البيانات: {e}")
