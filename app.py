import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# إعدادات الصفحة - تصميم داكن مطابق لـ RasedSPX / Webull
st.set_page_config(page_title="راصد الأسهم - Rased Stocks", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        text-align: center;
    }
    .badge-green { color: #2ea043; font-weight: bold; }
    .badge-red { color: #da3633; font-weight: bold; }
    .badge-orange { color: #d29922; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ راصد الشركات والصفقات الكبيرة")

# القائمة الجانبية للإعدادات
st.sidebar.header("⚙️ إعدادات الراصد")
ticker_symbol = st.sidebar.text_input("رمز الشركة (Ticker)", value="NVDA").upper()
min_trade_val = st.sidebar.number_input("حد الصفقات الكبيرة ($)", value=50000, step=10000)

if ticker_symbol:
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.fast_info
        
        current_price = info['lastPrice']
        prev_close = info['previousClose']
        change = current_price - prev_close
        pct_change = (change / prev_close) * 100
        
        # 1. لوحة تفاصيل السهم والاتجاهات
        st.subheader(f"📌 {ticker_symbol} - ملخص الحركة والزخم")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            color = "🟢" if change >= 0 else "🔴"
            st.markdown(f"""
            <div class="metric-card">
                <h4>السعر الحالي</h4>
                <h2>${current_price:.2f}</h2>
                <p>{color} {change:+.2f} ({pct_change:+.2f}%)</p>
            </div>
            """, unsafe_allow_html=True)
            
        # خوارزمية تحديد الاتجاهات والزخم
        hist = stock.history(period="5d", interval="15m")
        if not hist.empty:
            sma_fast = hist['Close'].rolling(5).mean().iloc[-1]
            sma_slow = hist['Close'].rolling(20).mean().iloc[-1]
            rsi_val = 50  # افتراضي
            
            # الاتجاه العام واللحظي
            if current_price > sma_fast and sma_fast > sma_slow:
                trend_gen = "صاعد 🚀"
                trend_inst = "صاعد 🟢"
                flow_type = "دخول Calls 🟢"
            elif current_price < sma_fast and sma_fast < sma_slow:
                trend_gen = "هابط 🔻"
                trend_inst = "هابط 🔴"
                flow_type = "دخول Puts 🔴"
            else:
                trend_gen = "عرضي 🟡"
                trend_inst = "متذبذب 🟡"
                flow_type = "سيولة محايدة 🟡"

            # الزخم
            volume_momentum = hist['Volume'].iloc[-1] - hist['Volume'].mean()
            momentum_str = f"+{int(abs(volume_momentum)):,}" if volume_momentum > 0 else f"-{int(abs(volume_momentum)):,}"
        else:
            trend_gen, trend_inst, flow_type, momentum_str = "غير متاح", "غير متاح", "غير متاح", "0"

        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h4>زخم السوق</h4>
                <h3>⚡ {momentum_str}</h3>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h4>الاتجاه العام / اللحظي</h4>
                <p>العام: <b>{trend_gen}</b></p>
                <p>اللحظي: <b>{trend_inst}</b></p>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h4>السيولة اللحظية</h4>
                <h3>{flow_type}</h3>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # 2. جدول الصفقات الكبيرة والتحليلات اللحظية (Whale & Block Trades)
        st.subheader("🐳 الصفقات الكبيرة اللحظية (Whale Trades Flow)")
        
        expirations = stock.options
        if expirations:
            selected_exp = st.selectbox("اختر تاريخ انتهاء العقود", options=expirations[:3])
            opt = stock.option_chain(selected_exp)
            
            calls = opt.calls.copy()
            puts = opt.puts.copy()
            calls['Option_Type'] = 'Call'
            puts['Option_Type'] = 'Put'
            
            df_options = pd.concat([calls, puts])
            df_options['Trade_Value'] = df_options['volume'] * df_options['lastPrice'] * 100
            
            # تصفية الصفقات الكبيرة فقط بناءً على الحد الأدنى للقيمة
            df_large = df_options[df_options['Trade_Value'] >= min_trade_val].copy()
            
            if not df_large.empty:
                def classify_trade(row):
                    val = row['Trade_Value']
                    opt_type = row['Option_Type']
                    last = row['lastPrice']
                    ask = row['ask']
                    bid = row['bid']
                    
                    # تصنيف الجهة (مؤسسة vs فرد)
                    entity = "🐋 مؤسسة" if val >= 200000 else "👤 فرد"
                    
                    # تصنيف النوع والتوقع (شراء/بيع - لونق/شورت)
                    if ask > 0 and last >= ask:
                        action = "شراء (Ask)"
                        sentiment = "🚀 توقع صعود قوي" if opt_type == 'Call' else "🐻 توقع هبوط قوي"
                    elif bid > 0 and last <= bid:
                        action = "بيع/شورت (Bid)"
                        sentiment = "🐻 فتح شورت / تفريغ" if opt_type == 'Call' else "🛡️ فتح شورت بيع / دعم"
                    else:
                        action = "حياد"
                        sentiment = "🟡 صفقة محايدة"
                        
                    return pd.Series([f"{entity} {action}", sentiment])

                df_large[['النوع والمنفذ', 'الوصف والتوقع']] = df_large.apply(classify_trade, axis=1)
                
                # إعداد الجدول للعرض المطابق للراصد
                df_display = pd.DataFrame({
                    'النوع': df_large['Option_Type'].apply(lambda x: 'C (كول)' if x == 'Call' else 'P (بوت)'),
                    'الإسترايك': df_large['strike'].apply(lambda x: f"${x:g}"),
                    'عدد العقود': df_large['volume'].fillna(0).astype(int),
                    'سعر التنفيذ': df_large['lastPrice'].apply(lambda x: f"${x:.2f}"),
                    'قيمة الصفقة': df_large['Trade_Value'].apply(lambda x: f"${x/1000:.1f}K" if x < 1000000 else f"${x/1000000:.2f}M"),
                    'المنفذ والاتجاه': df_large['النوع والمنفذ'],
                    'الوصف والتوقع': df_large['الوصف والتوقع']
                }).sort_values('قيمة الصفقة', ascending=False)

                st.dataframe(df_display, use_container_width=True, height=500)
            else:
                st.info(f"لا توجد صفقات كبيرة تتجاوز ${min_trade_val:,} لتاريخ الإغلاق المحدد حالياً.")

    except Exception as e:
        st.error(f"حدث خطأ أثناء جلب البيانات: {e}")
