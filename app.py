import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os

# إعدادات الواجهة الاحترافية (Dark Dashboard Theme)
st.set_page_config(page_title="راصد الأسهم والتوصيات الدقيقة", layout="wide")

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

st.title("⚡ منصة الراصد الذكي والتوصيات المخصصة (Max $2.00)")

# ملف سجل التوصيات
LOG_FILE = "recommendations_targets_log.csv"
if not os.path.exists(LOG_FILE):
    df_empty = pd.DataFrame(columns=[
        "ID", "Date", "Ticker", "Type", "Strike", "Expiration", 
        "Entry_Contract_Price", "Target_1", "Target_2", "Stop_Loss"
    ])
    df_empty.to_csv(LOG_FILE, index=False)

# القائمة الجانبية
st.sidebar.header("⚙️ إعدادات المحلل")
ticker_symbol = st.sidebar.text_input("رمز الشركة (Ticker)", value="NVDA").upper()
max_contract_price = st.sidebar.number_input("الحد الأقصى لسعر العقد ($)", value=2.00, step=0.10)
whale_filter = st.sidebar.slider("حد صفقات الحيتان ($)", min_value=50000, max_value=1000000, value=150000, step=50000)
min_vol_filter = st.sidebar.number_input("الحد الأدنى للفوليوم الملحوظ", value=500, step=100)

if ticker_symbol:
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.fast_info
        
        price = info['lastPrice']
        prev_close = info['previousClose']
        change = price - prev_close
        pct_change = (change / prev_close) * 100
        
        # 1. تحليل الاتجاهات والزخم
        hist = stock.history(period="5d", interval="15m")
        
        if not hist.empty:
            sma20 = hist['Close'].rolling(20).mean().iloc[-1]
            sma50 = hist['Close'].rolling(50).mean().iloc[-1]
            
            if price > sma20 and sma20 > sma50:
                overall_trend = "صاعد قوي 🚀"
                instant_trend = "صاعد 🟢"
                momentum_status = "زخم شرائي عالٍ 🟢"
                signal_type = "CALL"
            elif price < sma20 and sma20 < sma50:
                overall_trend = "هابط 🔻"
                instant_trend = "هابط 🔴"
                momentum_status = "زخم بيعي ضاغط 🔴"
                signal_type = "PUT"
            else:
                overall_trend = "عرضي 🟡"
                instant_trend = "متذبذب 🟡"
                momentum_status = "زخم محايد ⚪"
                signal_type = "NEUTRAL"
        else:
            overall_trend, instant_trend, momentum_status, signal_type = "غير متاح", "غير متاح", "غير متاح", "NEUTRAL"

        # عرض ملخص السهم
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"<div class='card-box'><h4>السعر اللحظي</h4><h2>${price:.2f}</h2><p>{'🟢' if change>=0 else '🔴'} {change:+.2f} ({pct_change:+.2f}%)</p></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='card-box'><h4>الاتجاه العام</h4><h3>{overall_trend}</h3></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='card-box'><h4>الاتجاه اللحظي</h4><h3>{instant_trend}</h3></div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div class='card-box'><h4>زخم السوق</h4><h3>{momentum_status}</h3></div>", unsafe_allow_html=True)

        st.divider()

        # 2. توليد التوصية المباشرة
        st.subheader("🎯 التوصية المباشرة (شرط سعر العقد ≤ $2.00)")
        expirations = stock.options
        
        if expirations:
            target_exp = expirations[0]
            opt = stock.option_chain(target_exp)
            selected_contract = None
            
            if signal_type == "CALL":
                calls = opt.calls.copy()
                calls['Trade_Value'] = calls['volume'] * calls['lastPrice'] * 100
                valid_calls = calls[(calls['lastPrice'] <= max_contract_price) & (calls['lastPrice'] > 0)]
                if not valid_calls.empty:
                    selected_contract = valid_calls.sort_values('Trade_Value', ascending=False).iloc[0]
            
            elif signal_type == "PUT":
                puts = opt.puts.copy()
                puts['Trade_Value'] = puts['volume'] * puts['lastPrice'] * 100
                valid_puts = puts[(puts['lastPrice'] <= max_contract_price) & (puts['lastPrice'] > 0)]
                if not valid_puts.empty:
                    selected_contract = valid_puts.sort_values('Trade_Value', ascending=False).iloc[0]

            if selected_contract is not None:
                strike_price = selected_contract['strike']
                contract_price = selected_contract['lastPrice']
                c_type = "CALL" if signal_type == "CALL" else "PUT"
                
                target_1 = contract_price * 1.20
                target_2 = contract_price * 1.50
                stop_loss = contract_price * 0.80
                border_color = "#2ea043" if c_type == "CALL" else "#da3633"
                
                st.markdown(f"""
                <div class='recommendation-box' style='border-color: {border_color};'>
                    <h3>🟢 التوصية الدقيقة: {ticker_symbol} - ${strike_price:g} {c_type}</h3>
                    <p><b>تاريخ الانتهاء:</b> {target_exp} | <b>سعر دخول العقد:</b> <span style='color:#f0883e; font-size:1.3em;'>${contract_price:.2f}</span></p>
                    <hr style='border-color: #30363d;'>
                    <div style='display: flex; justify-content: space-around; text-align: center;'>
                        <div><h4>🎯 الهدف الأول (+20%)</h4><h3 style='color: #2ea043;'>${target_1:.2f}</h3></div>
                        <div><h4>🚀 الهدف الثاني (+50%)</h4><h3 style='color: #58a6ff;'>${target_2:.2f}</h3></div>
                        <div><h4>🛑 وقف الخسارة (-20%)</h4><h3 style='color: #da3633;'>${stop_loss:.2f}</h3></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("📌 حفظ التوصية في جدول المتابعة"):
                    log_df = pd.read_csv(LOG_FILE)
                    new_id = int(datetime.now().timestamp())
                    new_row = {
                        "ID": new_id,
                        "Date": datetime.now().strftime('%Y-%m-%d %H:%M'),
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
                    st.success("تم حفظ الصفقة في جدول المتابعة بنجاح!")
            else:
                st.info(f"لا يوجد عقد {signal_type} بسعر أقل من ${max_contract_price:.2f} حالياً.")

        st.divider()

        # 3. جدول متابعة الصفقات المنظم مع زر الحذف التفاعلي
        st.subheader("📈 جدول متابعة الصفقات الحالية")
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
                            achievement = "🚀 الهدف 2 (+50%)"
                        elif curr_p >= t1:
                            achievement = "🎯 الهدف 1 (+20%)"
                        elif curr_p < entry_price * 0.8:
                            achievement = "🛑 وقف الخسارة"
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
                    "رمز الصفقة": int(row['ID']) if 'ID' in row and not pd.isna(row['ID']) else idx,
                    "التاريخ": row['Date'],
                    "الشركة والعقد": f"{t_ticker} ${t_strike:g} {t_type}",
                    "تاريخ الانتهاء": t_exp,
                    "سعر الدخول": f"${entry_price:.2f}",
                    "الهدف 1": f"${t1:.2f}",
                    "الهدف 2": f"${t2:.2f}",
                    "السعر الحالي": f"${curr_p:.2f}" if isinstance(curr_p, float) else curr_p,
                    "الربح/الخسارة": f"{roi:+.1f}%",
                    "الحالة": achievement
                })
            
            df_track = pd.DataFrame(rows_data)
            st.dataframe(df_track, use_container_width=True)
            
            # قسم خيارات الحذف السريعة للصفقات المنتهية
            del_id = st.selectbox("اختر الصفقة لحذفها من الجدول:", options=df_track["رمز الصفقة"].tolist())
            if st.button("🗑️ حذف الصفقة المحددة"):
                if 'ID' in log_df.columns:
                    log_df = log_df[log_df['ID'] != del_id]
                else:
                    log_df = log_df.drop(del_id)
                log_df.to_csv(LOG_FILE, index=False)
                st.rerun()
        else:
            st.info("لا توجد صفقات في جدول المتابعة حالياً.")

        st.divider()

        # 4. جدول تدفق صفقات الحيتان الشامل لسعر العقد والسترايكات
        st.subheader("🐋 رصد صفقات الحيتان (يشمل سعر العقد والفوليوم العالي)")
        selected_exp = st.selectbox("عرض صفقات الحيتان حسب التاريخ:", options=expirations[:3])
        opt_data = stock.option_chain(selected_exp)
        
        calls_df, puts_df = opt_data.calls.copy(), opt_data.puts.copy()
        calls_df['Type'], puts_df['Type'] = 'Call 🟢', 'Put 🔴'
        df_all = pd.concat([calls_df, puts_df])
        df_all['Trade_Value'] = df_all['volume'] * df_all['lastPrice'] * 100
        
        # تصفية السترايكات القريبة والفوليوم العالي
        lower_bound, upper_bound = price * 0.90, price * 1.10
        whales = df_all[(df_all['strike'] >= lower_bound) & (df_all['strike'] <= upper_bound)].copy()
        whales = whales[(whales['Trade_Value'] >= whale_filter) & (whales['volume'] >= min_vol_filter)].copy()
        
        if not whales.empty:
            df_display = pd.DataFrame({
                'النوع': whales['Type'],
                'السترايك': whales['strike'].apply(lambda x: f"${x:g}"),
                'سعر العقد (Price)': whales['lastPrice'].apply(lambda x: f"${x:.2f}"),
                'تاريخ العقد': selected_exp,
                'عدد العقود (Volume)': whales['volume'].fillna(0).astype(int),
                'سعر العرض (Ask)': whales['ask'].apply(lambda x: f"${x:.2f}"),
                'سعر الطلب (Bid)': whales['bid'].apply(lambda x: f"${x:.2f}"),
                'قيمة الصفقة الإجمالية': whales['Trade_Value'].apply(lambda x: f"${x/1000:.1f}K" if x < 1000000 else f"${x/1000000:.2f}M")
            }).sort_values('عدد العقود (Volume)', ascending=False)

            st.dataframe(df_display, use_container_width=True, height=450)
        else:
            st.info(f"لا توجد صفقات حيتان ملحوظة قريبة من السعر حالياً (${price:.2f}).")

    except Exception as e:
        st.error(f"حدث خطأ أثناء تحميل البيانات: {e}")
