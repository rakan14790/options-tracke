import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os

# إعدادات الواجهة الاحترافية (Dark Dashboard Theme)
st.set_page_config(page_title="راصد التداول الصارم | $200 Account", layout="wide")

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
    .recommendation-box-win {
        background-color: #1c2128;
        border: 2px solid #2ea043;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 25px;
    }
    .recommendation-box-wait {
        background-color: #1c2128;
        border: 2px solid #d29922;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ راصد التداول الصارم (إدارة محفظة الـ $200)")

# ملف سجل المفضلة والمتابعة
LOG_FILE = "favorites_log.csv"
if not os.path.exists(LOG_FILE):
    df_empty = pd.DataFrame(columns=[
        "ID", "Date", "Ticker", "Type", "Strike", "Expiration", 
        "Entry_Contract_Price", "Target_1", "Target_2", "Stop_Loss"
    ])
    df_empty.to_csv(LOG_FILE, index=False)

# القائمة الجانبية للتحكم
st.sidebar.header("⚙️ إعدادات المحفظة والبحث")
ticker_symbol = st.sidebar.text_input("رمز الشركة (Ticker)", value="NVDA").upper()
max_contract_price = st.sidebar.number_input("الحد الأقصى لسعر العقد ($)", value=1.50, step=0.10)
whale_filter = st.sidebar.slider("حد صفقات الحيتان ($)", min_value=50000, max_value=1000000, value=100000, step=25000)

if ticker_symbol:
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.fast_info
        
        price = info['lastPrice']
        prev_close = info['previousClose']
        change = price - prev_close
        pct_change = (change / prev_close) * 100
        
        # 1. تحليل الاتجاهات اللحظية بدقة
        hist = stock.history(period="5d", interval="15m")
        
        if not hist.empty:
            sma20 = hist['Close'].rolling(20).mean().iloc[-1]
            sma50 = hist['Close'].rolling(50).mean().iloc[-1]
            vol_mom = hist['Volume'].iloc[-1] - hist['Volume'].mean()
            
            if price > sma20 and sma20 > sma50 and vol_mom > 0:
                overall_trend = "صاعد قوي 🚀"
                instant_trend = "صاعد 🟢"
                momentum_status = "زخم شرائي عالي 🔥"
                signal_type = "CALL"
            elif price < sma20 and sma20 < sma50 and vol_mom > 0:
                overall_trend = "هابط 🔻"
                instant_trend = "هابط 🔴"
                momentum_status = "زخم بيعي ضاغط 🔴"
                signal_type = "PUT"
            else:
                overall_trend = "عرضي / غير مؤكد 🟡"
                instant_trend = "متذبذب 🟡"
                momentum_status = "زخم ضعيف ⚪"
                signal_type = "NEUTRAL"
        else:
            overall_trend, instant_trend, momentum_status, signal_type = "غير متاح", "غير متاح", "غير متاح", "NEUTRAL"

        # عرض الكروت العلوية
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"<div class='card-box'><h4>السعر اللحظي</h4><h2>${price:.2f}</h2><p>{'🟢' if change>=0 else '🔴'} {change:+.2f} ({pct_change:+.2f}%)</p></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='card-box'><h4>الاتجاه العام</h4><h3>{overall_trend}</h3></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='card-box'><h4>الاتجاه اللحظي</h4><h3>{instant_trend}</h3></div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div class='card-box'><h4>زخم التداول</h4><h3>{momentum_status}</h3></div>", unsafe_allow_html=True)

        st.divider()

        # 2. قسم التوصية عالية الدقة (High-Probability Signal)
        st.subheader("🎯 التوصية عالية التأكيد (مخاطرة منخفضة)")
        expirations = stock.options
        
        if expirations and signal_type != "NEUTRAL":
            target_exp = expirations[0]
            opt = stock.option_chain(target_exp)
            selected_contract = None
            
            if signal_type == "CALL":
                calls = opt.calls.copy()
                calls['Trade_Value'] = calls['volume'] * calls['lastPrice'] * 100
                valid_calls = calls[(calls['lastPrice'] <= max_contract_price) & (calls['lastPrice'] >= 0.30)]
                if not valid_calls.empty:
                    selected_contract = valid_calls.sort_values('Trade_Value', ascending=False).iloc[0]
            
            elif signal_type == "PUT":
                puts = opt.puts.copy()
                puts['Trade_Value'] = puts['volume'] * puts['lastPrice'] * 100
                valid_puts = puts[(puts['lastPrice'] <= max_contract_price) & (puts['lastPrice'] >= 0.30)]
                if not valid_puts.empty:
                    selected_contract = valid_puts.sort_values('Trade_Value', ascending=False).iloc[0]

            if selected_contract is not None:
                strike_price = selected_contract['strike']
                contract_price = selected_contract['lastPrice']
                c_type = "CALL" if signal_type == "CALL" else "PUT"
                
                target_1 = contract_price * 1.25  # +25%
                target_2 = contract_price * 1.50  # +50%
                stop_loss = contract_price * 0.85 # -15%
                
                st.markdown(f"""
                <div class='recommendation-box-win'>
                    <h3>🔥 فرصة دقيقة للـ $200: {ticker_symbol} - ${strike_price:g} {c_type}</h3>
                    <p><b>تاريخ العقد:</b> {target_exp} | <b>سعر الدخول الموصى به:</b> <span style='color:#f0883e; font-size:1.3em;'>${contract_price:.2f}</span> (${contract_price*100:.0f} للعقد)</p>
                    <hr style='border-color: #30363d;'>
                    <div style='display: flex; justify-content: space-around; text-align: center;'>
                        <div><h4>🎯 الهدف الأول (+25%)</h4><h3 style='color: #2ea043;'>${target_1:.2f}</h3></div>
                        <div><h4>🚀 الهدف الثاني (+50%)</h4><h3 style='color: #58a6ff;'>${target_2:.2f}</h3></div>
                        <div><h4>🛑 وقف الخسارة الصارم (-15%)</h4><h3 style='color: #da3633;'>${stop_loss:.2f}</h3></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("💖 إضافة التوصية فوراً إلى قائمة المتابعة"):
                    log_df = pd.read_csv(LOG_FILE)
                    new_id = int(datetime.now().timestamp())
                    new_row = {
                        "ID": new_id,
                        "Date": datetime.now().strftime('%m-%d %H:%M'),
                        "Ticker": ticker_symbol,
                        "Type": c_type,
                        "Strike": strike_price,
                        "Expiration": target_exp,
                        "Entry_Contract_Price": contract_price,
                        "Target_1": target_1,
                        "Target_2": target_2,
                        "Stop_Loss": stop_loss
                    }
                    log_df = pd.concat([log_df, pd.DataFrame([new_row])], ignore_index=True)
                    log_df.to_csv(LOG_FILE, index=False)
                    st.success("تم إضافة العقد إلى قائمة المفضلة والمتابعة 💖")
            else:
                st.info("لا يوجد عقد مناسب بشرط السعر والسيولة حالياً.")
        else:
            st.markdown("""
            <div class='recommendation-box-wait'>
                <h3>🛑 قرار المحفظة: عدم الدخول (امسك الكاش)</h3>
                <p>السوق في حالة تذبذب أو عدم توافق بين الاتجاه والزخم. لحماية الـ $200، ننتظر سيولة صريحة قبل الدخول.</p>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # 3. جدول الصفقات المفضلة والمتابعة (مع زر الإزالة 💔)
        st.subheader("💖 صفقات المتابعة والمفضلة (حفظ وحذف بنقرة)")
        log_df = pd.read_csv(LOG_FILE)
        
        if not log_df.empty:
            rows_data = []
            for idx, row in log_df.iterrows():
                t_ticker = row['Ticker']
                t_strike = float(row['Strike'])
                t_type = row['Type']
                t_exp = row['Expiration']
                entry_price = float(row['Entry_Contract_Price'])
                t1, t2 = float(row['Target_1']), float(row['Target_2'])
                
                try:
                    s_ticker = yf.Ticker(t_ticker)
                    s_opt = s_ticker.option_chain(t_exp)
                    chain = s_opt.calls if t_type == "CALL" else s_opt.puts
                    matched = chain[chain['strike'] == t_strike]
                    
                    if not matched.empty:
                        curr_p = float(matched['lastPrice'].values[0])
                        roi = ((curr_p - entry_price) / entry_price) * 100
                        
                        if curr_p >= t2:
                            achievement = "🚀 حقق الهدف الثاني (+50%)"
                        elif curr_p >= t1:
                            achievement = "🎯 حقق الهدف الأول (+25%)"
                        elif curr_p < entry_price * 0.85:
                            achievement = "🛑 ضرب وقف الخسارة"
                        else:
                            achievement = "⏳ قيد التداول"
                    else:
                        curr_p = "منتهي"
                        roi = 0.0
                        achievement = "⚪ انتهى العقد"
                except:
                    curr_p = entry_price
                    roi = 0.0
                    achievement = "🔄 جاري التحديث"

                rows_data.append({
                    "المعرف": int(row['ID']) if 'ID' in row and not pd.isna(row['ID']) else idx,
                    "الوقت": row['Date'],
                    "الرمز والعقد": f"{t_ticker} ${t_strike:g} {t_type}",
                    "الانتهاء": t_exp,
                    "سعر الدخول": f"${entry_price:.2f}",
                    "الهدف 1": f"${t1:.2f}",
                    "الهدف 2": f"${t2:.2f}",
                    "السعر الحالي": f"${curr_p:.2f}" if isinstance(curr_p, float) else curr_p,
                    "الربح / الخسارة": f"{roi:+.1f}%",
                    "الحالة": achievement
                })
            
            df_track = pd.DataFrame(rows_data)
            st.dataframe(df_track, use_container_width=True)
            
            # زر إزالة الصفقة من المفضلة
            remove_id = st.selectbox("اختر صفقة لإزالتها من المتابعة:", options=df_track["المعرف"].tolist())
            if st.button("💔 إزالة من المفضلة"):
                log_df = log_df[log_df['ID'] != remove_id]
                log_df.to_csv(LOG_FILE, index=False)
                st.rerun()
        else:
            st.info("لا توجد صفقات في المتابعة حالياً. اضغط على 💖 في التوصية لإضافتها هنا.")

        st.divider()

        # 4. جدول تدفق صفقات الحيتان (حول السعر اللحظي فقط)
        st.subheader("🐋 رصد صفقات الحيتان (السترايكات القريبة وسعر العقد اللحظي)")
        selected_exp = st.selectbox("تاريخ عقد الحيتان:", options=expirations[:3])
        opt_data = stock.option_chain(selected_exp)
        
        calls_df, puts_df = opt_data.calls.copy(), opt_data.puts.copy()
        calls_df['Type'], puts_df['Type'] = 'Call 🟢', 'Put 🔴'
        df_all = pd.concat([calls_df, puts_df])
        df_all['Trade_Value'] = df_all['volume'] * df_all['lastPrice'] * 100
        
        # تصفية السترايكات القريبة من سعر السهم الحالي بنسبة ±5% فقط
        lower_bound, upper_bound = price * 0.95, price * 1.05
        whales = df_all[(df_all['strike'] >= lower_bound) & (df_all['strike'] <= upper_bound)].copy()
        whales = whales[whales['Trade_Value'] >= whale_filter].copy()
        
        if not whales.empty:
            df_display = pd.DataFrame({
                'النوع': whales['Type'],
                'السترايك': whales['strike'].apply(lambda x: f"${x:g}"),
                'سعر العقد الحالي': whales['lastPrice'].apply(lambda x: f"${x:.2f}"),
                'العرض (Ask)': whales['ask'].apply(lambda x: f"${x:.2f}"),
                'الطلب (Bid)': whales['bid'].apply(lambda x: f"${x:.2f}"),
                'الحجم (Volume)': whales['volume'].fillna(0).astype(int),
                'إجمالي قيمة الصفقة': whales['Trade_Value'].apply(lambda x: f"${x/1000:.1f}K" if x < 1000000 else f"${x/1000000:.2f}M")
            }).sort_values('الحجم (Volume)', ascending=False)

            st.dataframe(df_display, use_container_width=True, height=420)
        else:
            st.info(f"لا توجد حركة حيتان مكثفة قريبة جداً من سعر السهم الحالي (${price:.2f}).")

    except Exception as e:
        st.error(f"حدث خطأ أثناء تحليل البيانات: {e}")
