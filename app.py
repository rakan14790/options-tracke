import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# إعدادات الواجهة الاحترافية (Dark Dashboard Theme)
st.set_page_config(page_title="منصة الراصد الذكي - Smart Order Flow", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .card-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin-bottom: 10px;
    }
    .buy-signal { color: #2ea043; font-weight: bold; font-size: 1.2em; }
    .sell-signal { color: #da3633; font-weight: bold; font-size: 1.2em; }
    .neutral-signal { color: #d29922; font-weight: bold; font-size: 1.2em; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ منصة الراصد الذكي للسيولة والصفقات الكبيرة")

# القائمة الجانبية للتحكم
st.sidebar.header("⚙️ إعدادات المحلل الذكي")
ticker_symbol = st.sidebar.text_input("رمز الشركة", value="NVDA").upper()
whale_filter = st.sidebar.slider("تصفية صفقات الحيتان (أكبر من $)", min_value=50000, max_value=1000000, value=150000, step=50000)

if ticker_symbol:
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.fast_info
        
        price = info['lastPrice']
        prev_close = info['previousClose']
        change_pct = ((price - prev_close) / prev_close) * 100
        
        # 1. كارت ملخص الاتجاه العام والتوصية اللحظية
        st.subheader(f"📊 تحليل الاتجاه وعمق السيولة: {ticker_symbol}")
        
        hist = stock.history(period="5d", interval="15m")
        
        if not hist.empty:
            # حساب المتوسطات والزخم
            sma20 = hist['Close'].rolling(20).mean().iloc[-1]
            sma50 = hist['Close'].rolling(50).mean().iloc[-1]
            volume_momentum = hist['Volume'].iloc[-1] - hist['Volume'].mean()
            
            # تحديد الاتجاه والزخم
            if price > sma20 and sma20 > sma50:
                overall_trend = "صاعد قوي 🚀"
                momentum_status = "زخم شرائي عالٍ 🟢"
                action_recommendation = "<span class='buy-signal'>🟢 مناطق دخول شرائية (Calls)</span>"
            elif price < sma20 and sma20 < sma50:
                overall_trend = "هابط 🔻"
                momentum_status = "زخم بيعي ضاغط 🔴"
                action_recommendation = "<span class='sell-signal'>🔴 مناطق ضغط بيعي / شورت (Puts)</span>"
            else:
                overall_trend = "عرضي / مذبذب 🟡"
                momentum_status = "زخم محايد ⚪"
                action_recommendation = "<span class='neutral-signal'>🟡 انتظار اتجاه واضح</span>"

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"<div class='card-box'><h4>السعر الحالي</h4><h2>${price:.2f}</h2><p>{'🟢' if change_pct>=0 else '🔴'} {change_pct:+.2f}%</p></div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div class='card-box'><h4>الاتجاه العام</h4><h3>{overall_trend}</h3></div>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"<div class='card-box'><h4>زخم السيولة</h4><h3>{momentum_status}</h3></div>", unsafe_allow_html=True)
            with col4:
                st.markdown(f"<div class='card-box'><h4>التوصية اللحظية</h4><h3>{action_recommendation}</h3></div>", unsafe_allow_html=True)

        st.divider()

        # 2. رصد صفقات الحيتان وعمق السوق بدون OI
        st.subheader("🐋 رصد صفقات الحيتان (Whale & Block Trades Flow)")
        
        expirations = stock.options
        if expirations:
            selected_exp = st.selectbox("اختر تاريخ الانتهاء للعقود", options=expirations[:3])
            opt = stock.option_chain(selected_exp)
            
            calls = opt.calls.copy()
            puts = opt.puts.copy()
            calls['Type'] = 'Call'
            puts['Type'] = 'Put'
            
            df_opt = pd.concat([calls, puts])
            df_opt['Trade_Value'] = df_opt['volume'] * df_opt['lastPrice'] * 100
            
            # تصفية الصفقات الكبيرة فقط
            whales = df_opt[df_opt['Trade_Value'] >= whale_filter].copy()
            
            if not whales.empty:
                def analyze_whale_trade(r):
                    val = r['Trade_Value']
                    opt_type = r['Type']
                    last = r['lastPrice']
                    ask = r['ask']
                    bid = r['bid']
                    
                    # تصنيف نوع المنفذ
                    entity = "🐋 مؤسسة ضخمة" if val >= 300000 else "🐳 حوت متوسط"
                    
                    # تحليل الاتجاه (شراء/بيع - لونق/شورت)
                    if ask > 0 and last >= ask:
                        if opt_type == 'Call':
                            return entity, "شراء Ask 🟢", "🚀 دخول صاعد (تجميع لونق)"
                        else:
                            return entity, "شراء Ask 🟢", "🐻 رهان هبوطي (شراء بوت)"
                    elif bid > 0 and last <= bid:
                        if opt_type == 'Call':
                            return entity, "بيع Bid 🔴", "⚠️ تفريغ / فتح شورت كول"
                        else:
                            return entity, "بيع Bid 🔴", "🛡️ فتح شورت بوت (جدار دعم)"
                    else:
                        return entity, "تنفيذ محايد 🟡", "⚪ صفقة موازنة"

                whales[['Entity', 'Execution', 'Signal']] = whales.apply(analyze_whale_trade, axis=1, result_type='expand')
                
                # تنظيم الجدول للعرض
                df_show = pd.DataFrame({
                    'النوع': whales['Type'].apply(lambda x: 'Call 🟢' if x == 'Call' else 'Put 🔴'),
                    'السترايك': whales['strike'].apply(lambda x: f"${x:g}"),
                    'عدد العقود': whales['volume'].fillna(0).astype(int),
                    'سعر التنفيذ': whales['lastPrice'].apply(lambda x: f"${x:.2f}"),
                    'قيمة الصفقة': whales['Trade_Value'].apply(lambda x: f"${x/1000:.1f}K" if x < 1000000 else f"${x/1000000:.2f}M"),
                    'المنفذ': whales['Entity'],
                    'طبيعة التنفيذ': whales['Execution'],
                    'توقعات الحركة (Signal)': whales['Signal']
                }).sort_values('قيمة الصفقة', ascending=False)

                st.dataframe(df_show, use_container_width=True, height=520)
            else:
                st.info(f"لا توجد صفقات حيتان تتجاوز ${whale_filter:,} حالياً لهذا التاريخ.")

    except Exception as e:
        st.error(f"حدث خطأ أثناء الاتصال بالبيانات: {e}")
