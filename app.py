import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# إعدادات الواجهة الاحترافية (Dark Dashboard Theme)
st.set_page_config(page_title="منصة التوصيات والراصد الذكي", layout="wide")

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
    .recommendation-box {
        background-color: #1c2128;
        border: 2px solid #2ea043;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 25px;
    }
    .buy-signal { color: #2ea043; font-weight: bold; font-size: 1.3em; }
    .sell-signal { color: #da3633; font-weight: bold; font-size: 1.3em; }
    .neutral-signal { color: #d29922; font-weight: bold; font-size: 1.3em; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ منصة التوصيات الذكية ورصد صفقات الحيتان")

# القائمة الجانبية للتحكم
st.sidebar.header("⚙️ إعدادات المحلل")
ticker_symbol = st.sidebar.text_input("رمز الشركة (Ticker)", value="NVDA").upper()
whale_filter = st.sidebar.slider("حد صفقات الحيتان ($)", min_value=50000, max_value=1000000, value=150000, step=50000)

if ticker_symbol:
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.fast_info
        
        price = info['lastPrice']
        prev_close = info['previousClose']
        change_pct = ((price - prev_close) / prev_close) * 100
        
        # 1. كارت ملخص الاتجاه العام والزخم
        hist = stock.history(period="5d", interval="15m")
        
        if not hist.empty:
            sma20 = hist['Close'].rolling(20).mean().iloc[-1]
            sma50 = hist['Close'].rolling(50).mean().iloc[-1]
            
            if price > sma20 and sma20 > sma50:
                overall_trend = "صاعد قوي 🚀"
                momentum_status = "زخم شرائي عالٍ 🟢"
                signal_type = "CALL"
            elif price < sma20 and sma20 < sma50:
                overall_trend = "هابط 🔻"
                momentum_status = "زخم بيعي ضاغط 🔴"
                signal_type = "PUT"
            else:
                overall_trend = "عرضي / مذبذب 🟡"
                momentum_status = "زخم محايد ⚪"
                signal_type = "NEUTRAL"

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"<div class='card-box'><h4>السعر الحالي</h4><h2>${price:.2f}</h2><p>{'🟢' if change_pct>=0 else '🔴'} {change_pct:+.2f}%</p></div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div class='card-box'><h4>الاتجاه اللحظي</h4><h3>{overall_trend}</h3></div>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"<div class='card-box'><h4>زخم التداول</h4><h3>{momentum_status}</h3></div>", unsafe_allow_html=True)

        st.divider()

        # 2. قسم مولد التوصية المباشرة مع ترشيح العقد والتاريخ
        st.subheader("🎯 التوصية المقترحة وبطاقة العقد")
        
        expirations = stock.options
        if expirations:
            # اختيار أقرب تاريخ استحقاق مناسب
            target_exp = expirations[0] 
            opt = stock.option_chain(target_exp)
            
            if signal_type == "CALL":
                # البحث عن أكثر عقد Call نشاطاً بالقرب من السعر الحالي
                calls = opt.calls.copy()
                calls['Trade_Value'] = calls['volume'] * calls['lastPrice'] * 100
                top_contract = calls[calls['strike'] >= price].sort_values('Trade_Value', ascending=False).iloc[0] if not calls.empty else None
                
                if top_contract is not None:
                    strike_price = top_contract['strike']
                    contract_price = top_contract['lastPrice']
                    volume = int(top_contract['volume']) if not np.isnan(top_contract['volume']) else 0
                    
                    st.markdown(f"""
                    <div class='recommendation-box'>
                        <h3 class='buy-signal'>🟢 توصية شراء عقد (CALL Option)</h3>
                        <p style='font-size: 1.1em;'><b>رمز السهم:</b> {ticker_symbol} | <b>سعر السهم اللحظي:</b> ${price:.2f}</p>
                        <hr style='border-color: #30363d;'>
                        <div style='display: flex; justify-content: space-around; text-align: center;'>
                            <div><h4>تاريخ العقد (Exp)</h4><h3 style='color: #58a6ff;'>{target_exp}</h3></div>
                            <div><h4>السترايك (Strike)</h4><h3 style='color: #2ea043;'>${strike_price:g} CALL</h3></div>
                            <div><h4>سعر العقد التقديري</h4><h3 style='color: #f0883e;'>${contract_price:.2f}</h3></div>
                            <div><h4>حجم سيولة العقد</h4><h3>{volume:,} عقد</h3></div>
                        </div>
                        <p style='margin-top: 15px; color: #8b949e;'>💡 <b>سبب التوصية:</b> تم رصد تدفق سيولة شرائية وزخم صاعد على هذا السترايك من قبل الحيتان.</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            elif signal_type == "PUT":
                # البحث عن أكثر عقد Put نشاطاً بالقرب من السعر الحالي
                puts = opt.puts.copy()
                puts['Trade_Value'] = puts['volume'] * puts['lastPrice'] * 100
                top_contract = puts[puts['strike'] <= price].sort_values('Trade_Value', ascending=False).iloc[0] if not puts.empty else None
                
                if top_contract is not None:
                    strike_price = top_contract['strike']
                    contract_price = top_contract['lastPrice']
                    volume = int(top_contract['volume']) if not np.isnan(top_contract['volume']) else 0
                    
                    st.markdown(f"""
                    <div class='recommendation-box' style='border-color: #da3633;'>
                        <h3 class='sell-signal'>🔴 توصية شراء عقد (PUT Option / Short)</h3>
                        <p style='font-size: 1.1em;'><b>رمز السهم:</b> {ticker_symbol} | <b>سعر السهم اللحظي:</b> ${price:.2f}</p>
                        <hr style='border-color: #30363d;'>
                        <div style='display: flex; justify-content: space-around; text-align: center;'>
                            <div><h4>تاريخ العقد (Exp)</h4><h3 style='color: #58a6ff;'>{target_exp}</h3></div>
                            <div><h4>السترايك (Strike)</h4><h3 style='color: #da3633;'>${strike_price:g} PUT</h3></div>
                            <div><h4>سعر العقد التقديري</h4><h3 style='color: #f0883e;'>${contract_price:.2f}</h3></div>
                            <div><h4>حجم سيولة العقد</h4><h3>{volume:,} عقد</h3></div>
                        </div>
                        <p style='margin-top: 15px; color: #8b949e;'>💡 <b>سبب التوصية:</b> تم رصد ضغط بيعي وزخم هابط وتجميع عقود هبوط من المؤسسات.</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class='recommendation-box' style='border-color: #d29922;'>
                    <h3 class='neutral-signal'>🟡 التوصية اللحظية: الانتظار والحياد</h3>
                    <p>السهم يتحرك في نطاق عرضي ومذبذب حالياً. يُفضل انتظار خروج سيولة حيتان واضحة لإنشاء توصية دقيقة.</p>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # 3. جدول تدفق صفقات الحيتان المباشر
        st.subheader("🐋 رصد صفقات الحيتان (Whale Trades Flow)")
        
        selected_exp = st.selectbox("عرض كافة الصفقات الكبيرة حسب التاريخ:", options=expirations[:3])
        opt_data = stock.option_chain(selected_exp)
        
        calls_df = opt_data.calls.copy()
        puts_df = opt_data.puts.copy()
        calls_df['Type'] = 'Call'
        puts_df['Type'] = 'Put'
        
        df_all = pd.concat([calls_df, puts_df])
        df_all['Trade_Value'] = df_all['volume'] * df_all['lastPrice'] * 100
        
        whales = df_all[df_all['Trade_Value'] >= whale_filter].copy()
        
        if not whales.empty:
            def analyze_whale(r):
                val = r['Trade_Value']
                opt_type = r['Type']
                last = r['lastPrice']
                ask = r['ask']
                bid = r['bid']
                
                entity = "🐋 مؤسسة ضخمة" if val >= 300000 else "🐳 حوت متوسط"
                
                if ask > 0 and last >= ask:
                    action = "شراء Ask 🟢"
                    sig = "🚀 دخول صاعد (تجميع)" if opt_type == 'Call' else "🐻 رهان هبوطي"
                elif bid > 0 and last <= bid:
                    action = "بيع Bid 🔴"
                    sig = "⚠️ تفريغ / شورت" if opt_type == 'Call' else "🛡️ بيع بوت (دعم)"
                else:
                    action = "تنفيذ محايد 🟡"
                    sig = "⚪ صفقة موازنة"
                    
                return pd.Series([entity, action, sig])

            whales[['Entity', 'Execution', 'Signal']] = whales.apply(analyze_whale, axis=1)
            
            df_display = pd.DataFrame({
                'النوع': whales['Type'].apply(lambda x: 'Call 🟢' if x == 'Call' else 'Put 🔴'),
                'السترايك': whales['strike'].apply(lambda x: f"${x:g}"),
                'تاريخ العقد': selected_exp,
                'عدد العقود': whales['volume'].fillna(0).astype(int),
                'سعر التنفيذ': whales['lastPrice'].apply(lambda x: f"${x:.2f}"),
                'قيمة الصفقة': whales['Trade_Value'].apply(lambda x: f"${x/1000:.1f}K" if x < 1000000 else f"${x/1000000:.2f}M"),
                'المنفذ': whales['Entity'],
                'توقعات الحركة': whales['Signal']
            }).sort_values('قيمة الصفقة', ascending=False)

            st.dataframe(df_display, use_container_width=True, height=450)
        else:
            st.info(f"لا توجد صفقات حيتان تتجاوز ${whale_filter:,} لهذا التاريخ.")

    except Exception as e:
        st.error(f"حدث خطأ أثناء تحميل البيانات: {e}")
