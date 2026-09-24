import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os

# إعدادات الواجهة الاحترافية
st.set_page_config(page_title="منصة التوصيات وتحديد الأهداف", layout="wide")

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
    </style>
""", unsafe_allow_html=True)

st.title("⚡ راصد التوصيات والأهداف - تتبع أداء عقود الأوبشن")

LOG_FILE = "recommendations_targets_log.csv"

# إنشاء الملف إذا لم يكن موجوداً
if not os.path.exists(LOG_FILE):
    df_empty = pd.DataFrame(columns=[
        "Date", "Ticker", "Type", "Strike", "Expiration", 
        "Entry_Contract_Price", "Target_1", "Target_2", "Stop_Loss", "Status"
    ])
    df_empty.to_csv(LOG_FILE, index=False)

# القائمة الجانبية
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
        
        # 1. كارت ملخص السهم
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='card-box'><h4>السعر اللحظي</h4><h2>${price:.2f}</h2><p>{'🟢' if change_pct>=0 else '🔴'} {change_pct:+.2f}%</p></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='card-box'><h4>السهم</h4><h2>{ticker_symbol}</h2></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='card-box'><h4>تاريخ اليوم</h4><h2>{datetime.now().strftime('%Y-%m-%d')}</h2></div>", unsafe_allow_html=True)

        st.divider()

        # 2. توليد التوصية المباشرة وحساب الأهداف
        st.subheader("🎯 التوصية اللحظية الحالية مع الأهداف")
        expirations = stock.options
        
        if expirations:
            target_exp = expirations[0]
            opt = stock.option_chain(target_exp)
            
            hist = stock.history(period="5d", interval="15m")
            sma20 = hist['Close'].rolling(20).mean().iloc[-1] if not hist.empty else price
            
            rec_type = "CALL" if price >= sma20 else "PUT"
            
            if rec_type == "CALL":
                calls = opt.calls.copy()
                calls['Trade_Value'] = calls['volume'] * calls['lastPrice'] * 100
                top_contract = calls[calls['strike'] >= price].sort_values('Trade_Value', ascending=False).iloc[0]
            else:
                puts = opt.puts.copy()
                puts['Trade_Value'] = puts['volume'] * puts['lastPrice'] * 100
                top_contract = puts[puts['strike'] <= price].sort_values('Trade_Value', ascending=False).iloc[0]

            strike_price = top_contract['strike']
            contract_price = top_contract['lastPrice']
            
            # حساب الأهداف تلقائياً (الهدف الأول +20% / الهدف الثاني +50% / وقف الخسارة -20%)
            target_1 = contract_price * 1.20
            target_2 = contract_price * 1.50
            stop_loss = contract_price * 0.80
            
            st.markdown(f"""
            <div class='recommendation-box'>
                <h3>🟢 التوصية المقترحة: {ticker_symbol} - ${strike_price:g} {rec_type}</h3>
                <p><b>تاريخ الانتهاء:</b> {target_exp} | <b>سعر العقد الحالي (الدخول):</b> <span style='color:#f0883e; font-size:1.3em;'>${contract_price:.2f}</span></p>
                <hr style='border-color: #30363d;'>
                <div style='display: flex; justify-content: space-around; text-align: center;'>
                    <div><h4>🎯 الهدف الأول (+20%)</h4><h3 style='color: #2ea043;'>${target_1:.2f}</h3></div>
                    <div><h4>🚀 الهدف الثاني (+50%)</h4><h3 style='color: #58a6ff;'>${target_2:.2f}</h3></div>
                    <div><h4>🛑 وقف الخسارة (-20%)</h4><h3 style='color: #da3633;'>${stop_loss:.2f}</h3></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # زر لحفظ التوصية مع أهدافها في السجل
            if st.button("📌 حفظ التوصية والأهداف لتتبعها"):
                log_df = pd.read_csv(LOG_FILE)
                new_row = {
                    "Date": datetime.now().strftime('%Y-%m-%d %H:%M'),
                    "Ticker": ticker_symbol,
                    "Type": rec_type,
                    "Strike": strike_price,
                    "Expiration": target_exp,
                    "Entry_Contract_Price": contract_price,
                    "Target_1": target_1,
                    "Target_2": target_2,
                    "Stop_Loss": stop_loss,
                    "Status": "Active"
                }
                log_df = pd.concat([log_df, pd.DataFrame([new_row])], ignore_index=True)
                log_df.to_csv(LOG_FILE, index=False)
                st.success("تم حفظ التوصية والأهداف بنجاح!")

        st.divider()

        # 3. جدول تتبع التوصيات والأهداف
        st.subheader("📈 سجل متابعة أداء التوصيات وتحقيق الأهداف")
        
        log_df = pd.read_csv(LOG_FILE)
        
        if not log_df.empty:
            tracked_results = []
            
            for idx, row in log_df.iterrows():
                t_ticker = row['Ticker']
                t_strike = row['Strike']
                t_type = row['Type']
                t_exp = row['Expiration']
                entry_price = float(row['Entry_Contract_Price'])
                t1 = float(row['Target_1'])
                t2 = float(row['Target_2'])
                
                try:
                    s_ticker = yf.Ticker(t_ticker)
                    s_opt = s_ticker.option_chain(t_exp)
                    
                    chain = s_opt.calls if t_type == "CALL" else s_opt.puts
                    matched = chain[chain['strike'] == t_strike]
                    
                    if not matched.empty:
                        curr_p = matched['lastPrice'].values[0]
                        roi = ((curr_p - entry_price) / entry_price) * 100
                        
                        # حالة الهدف
                        if curr_p >= t2:
                            achievement = "🚀 تحقّق الهدف الثاني بالكامل (+50%)"
                        elif curr_p >= t1:
                            achievement = "🎯 تحقّق الهدف الأول (+20%)"
                        elif curr_p < entry_price * 0.8:
                            achievement = "🛑 ضرب وقف الخسارة"
                        else:
                            achievement = "⏳ قيد التداول"
                    else:
                        curr_p = "منتهي"
                        roi = 0
                        achievement = "⚪ انتهى العقد"
                except:
                    curr_p = entry_price
                    roi = 0
                    achievement = "🔄 جاري التحديث"

                tracked_results.append({
                    "تاريخ التوصية": row['Date'],
                    "الشركة والعقد": f"{t_ticker} ${t_strike:g} {t_type}",
                    "سعر الدخول": f"${entry_price:.2f}",
                    "الهدف 1": f"${t1:.2f}",
                    "الهدف 2": f"${t2:.2f}",
                    "سعر العقد الحالي": f"${curr_p:.2f}" if isinstance(curr_p, float) else curr_p,
                    "نسبة الربح/الخسارة": f"{roi:+.1f}%",
                    "حالة تحقيق الهدف": achievement
                })
                
            st.dataframe(pd.DataFrame(tracked_results), use_container_width=True)
        else:
            st.info("لا توجد توصيات محفوظة ومتبعة حالياً.")

    except Exception as e:
        st.error(f"حدث خطأ أثناء تحميل البيانات: {e}")
