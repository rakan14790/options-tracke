import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import os

# إعدادات الشاشة والواجهة الاحترافية (Dark Pro Trading Theme)
st.set_page_config(page_title="NVDA Institutional Order Flow Dashboard", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #080a0f; color: #e1e4e8; }
    .metric-card {
        background: linear-gradient(145deg, #10141d, #171c28);
        border: 1px solid #262c3a;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .profile-card {
        background: #0f131c;
        border: 1px solid #1f2636;
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .recommendation-box {
        background: linear-gradient(135deg, #0d2016 0%, #11291b 100%);
        border: 2px solid #2ea043;
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 25px;
    }
    .wait-box {
        background: linear-gradient(135deg, #241a0e 0%, #2e2111 100%);
        border: 2px solid #d29922;
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ منصة تتبع عمق السيولة والتدفق المؤسسي | NVDA & Stocks Pro")

# ملف المتابعة والمفضلة
LOG_FILE = "favorites_log.csv"
if not os.path.exists(LOG_FILE):
    df_empty = pd.DataFrame(columns=[
        "Date", "Ticker", "Type", "Strike", "Expiration", 
        "Entry_Contract_Price", "Target_1", "Target_2", "Stop_Loss"
    ])
    df_empty.to_csv(LOG_FILE, index=False)

# الشريط الجانبي للتحكم
st.sidebar.header("🎯 تخصيص المحفظة والشركة")
ticker_symbol = st.sidebar.text_input("رمز السهم", value="NVDA").upper()
max_contract_price = st.sidebar.number_input("الحد الأقصى لسعر العقد ($)", value=1.50, step=0.10)

if ticker_symbol:
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.fast_info
        
        price = info['lastPrice']
        prev_close = info['previousClose']
        change = price - prev_close
        pct_change = (change / prev_close) * 100
        
        expirations = stock.options

        # 1. تحليل الفوليوم بروفايل والعمق (Volume Profile Engine)
        poc_price = price
        call_wall = price
        put_wall = price
        imbalance_ratio = 50.0

        if expirations:
            target_exp = expirations[0]
            opt = stock.option_chain(target_exp)
            calls, puts = opt.calls.copy(), opt.puts.copy()

            if not calls.empty and not puts.empty:
                # تصفية السترايكات القريبة من السعر (±7.5%)
                c_near = calls[(calls['strike'] >= price * 0.925) & (calls['strike'] <= price * 1.075)]
                p_near = puts[(puts['strike'] >= price * 0.925) & (puts['strike'] <= price * 1.075)]

                total_call_vol = c_near['volume'].sum() if not c_near.empty else 1
                total_put_vol = p_near['volume'].sum() if not p_near.empty else 1
                
                # نسبة عدم التوازن بين الشراء والبيع (Order Flow Imbalance)
                imbalance_ratio = (total_call_vol / (total_call_vol + total_put_vol)) * 100

                # تحديد أسطح القاما والـ POC
                if not c_near.empty:
                    call_wall = c_near.sort_values('volume', ascending=False).iloc[0]['strike']
                if not p_near.empty:
                    put_wall = p_near.sort_values('volume', ascending=False).iloc[0]['strike']

                poc_price = call_wall if total_call_vol > total_put_vol else put_wall

        # 2. عرض كروت المؤشرات الحيوية
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"<div class='metric-card'><h4>السعر اللحظي</h4><h2>${price:.2f}</h2><p>{'🟢' if change>=0 else '🔴'} {change:+.2f} ({pct_change:+.2f}%)</p></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><h4>مستوى التجميع (POC)</h4><h2 style='color:#58a6ff;'>${poc_price:g}</h2><p>أعلى نقطة تداول</p></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><h4>جدار القاما (Call Wall)</h4><h2 style='color:#2ea043;'>${call_wall:g}</h2><p>هدف المقاومة/الجذب</p></div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div class='metric-card'><h4>خلل التدفق (Call/Put Ratio)</h4><h2>{imbalance_ratio:.1f}%</h2><p>{'سيطر الشرائيين 🟢' if imbalance_ratio>50 else 'سيطر البائعيين 🔴'}</p></div>", unsafe_allow_html=True)

        st.divider()

        # 3. الرسم البياني التفاعلي لعمق السيولة (Volume Profile & Footprint Heatmap)
        st.subheader(f"📊 عمق السيولة والفوليوم بروفايل المباشر ({ticker_symbol})")
        
        if expirations:
            target_exp = expirations[0]
            opt = stock.option_chain(target_exp)
            c_df, p_df = opt.calls.copy(), opt.puts.copy()
            
            c_df = c_df[(c_df['strike'] >= price * 0.93) & (c_df['strike'] <= price * 1.07)]
            p_df = p_df[(p_df['strike'] >= price * 0.93) & (p_df['strike'] <= price * 1.07)]

            fig = go.Figure()
            
            # سيولة الشراء (Call Buyers Volume)
            fig.add_trace(go.Bar(
                y=c_df['strike'],
                x=c_df['volume'],
                name='سيولة كول (Call Vol)',
                orientation='h',
                marker=dict(color='rgba(46, 160, 67, 0.85)')
            ))

            # سيولة البيع (Put Sellers/Buyers Volume)
            fig.add_trace(go.Bar(
                y=p_df['strike'],
                x=-p_df['volume'],
                name='سيولة بوت (Put Vol)',
                orientation='h',
                marker=dict(color='rgba(218, 54, 51, 0.85)')
            ))

            # خط السعر اللحظي
            fig.add_hline(y=price, line_dash="dash", line_color="#f0883e", annotation_text=f"السعر اللحظي الحالي (${price:.2f})")

            fig.update_layout(
                barmode='relative',
                title=dict(text=f"توزيع الفوليوم والسيولة على المستويات (تاريخ الانتهاء: {target_exp})", font=dict(color="#e1e4e8")),
                paper_bgcolor='#080a0f',
                plot_bgcolor='#0f131c',
                xaxis=dict(title="حجم التداول اللحظي (Volume Flow)", gridcolor='#161b22', zerolinecolor='#30363d'),
                yaxis=dict(title="مستويات السترايك ($)", gridcolor='#161b22', autorange="reversed"),
                legend=dict(font=dict(color="#e1e4e8")),
                height=450,
                margin=dict(l=20, r=20, t=40, b=20)
            )

            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # 4. التوصية الجاهزة وعالية التأكيد (+A Grade Setup)
        st.subheader("🎯 التوصية الفورية (إشارة دخول مؤكدة للـ $200)")
        
        hist = stock.history(period="5d", interval="15m")
        signal_type = "NEUTRAL"
        
        if not hist.empty:
            sma20 = hist['Close'].rolling(20).mean().iloc[-1]
            if price > sma20 and imbalance_ratio > 52:
                signal_type = "CALL"
            elif price < sma20 and imbalance_ratio < 48:
                signal_type = "PUT"

        if expirations and signal_type != "NEUTRAL":
            target_exp = expirations[0]
            opt = stock.option_chain(target_exp)
            selected_contract = None
            
            chain = opt.calls if signal_type == "CALL" else opt.puts
            chain['Trade_Value'] = chain['volume'] * chain['lastPrice'] * 100
            valid = chain[(chain['lastPrice'] <= max_contract_price) & (chain['lastPrice'] >= 0.30)]
            
            if not valid.empty:
                selected_contract = valid.sort_values('Trade_Value', ascending=False).iloc[0]

            if selected_contract is not None:
                strike_price = selected_contract['strike']
                contract_price = selected_contract['lastPrice']
                c_type = "CALL" if signal_type == "CALL" else "PUT"
                
                target_1 = contract_price * 1.25  # +25%
                target_2 = contract_price * 1.50  # +50%
                stop_loss = contract_price * 0.85 # -15%
                
                st.markdown(f"""
                <div class='recommendation-box'>
                    <h3>🏆 فرصة درجة (+A) على أسهم {ticker_symbol} - ${strike_price:g} {c_type}</h3>
                    <p><b>تاريخ الانتهاء:</b> {target_exp} | <b>سعر الدخول:</b> <span style='color:#f0883e; font-size:1.3em;'>${contract_price:.2f}</span> (${contract_price*100:.0f} للعقد)</p>
                    <p style='color:#8b949e;'>💡 <b>سبب الترشيح:</b> اختراق إيجابي لعمق السيولة مع تفوق فوليوم الـ {c_type} بنسبة {imbalance_ratio:.1f}%.</p>
                    <hr style='border-color: #30363d;'>
                    <div style='display: flex; justify-content: space-around; text-align: center;'>
                        <div><h4>🎯 الهدف الأول (+25%)</h4><h3 style='color: #2ea043;'>${target_1:.2f}</h3></div>
                        <div><h4>🚀 الهدف الثاني (+50%)</h4><h3 style='color: #58a6ff;'>${target_2:.2f}</h3></div>
                        <div><h4>🛑 وقف الخسارة (-15%)</h4><h3 style='color: #da3633;'>${stop_loss:.2f}</h3></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("💖 إضافة الفرصة إلى جدول المتابعة"):
                    log_df = pd.read_csv(LOG_FILE)
                    new_row = {
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
                    st.success("تم إضافة العقد بنجاح! 💖")
        else:
            st.markdown("""
            <div class='wait-box'>
                <h3>🛑 قرار المحفظة: امسك الكاش (Wait & Protect Capital)</h3>
                <p>لا يوجد انحياز صريح في عمق التداول وحجم السيولة حالياً. لحماية محفظتك، انتظر وضوح اتجاه السوق.</p>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # 5. جدول المتابعة المباشر (سهل وسريع الإزالة)
        st.subheader("💖 صفقات المتابعة والمفضلة")
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
                        
                        if curr_p >= t2: achievement = "🚀 الهدف 2 (+50%)"
                        elif curr_p >= t1: achievement = "🎯 الهدف 1 (+25%)"
                        elif curr_p < entry_price * 0.85: achievement = "🛑 ضرب وقف الخسارة"
                        else: achievement = "⏳ قيد التداول"
                    else:
                        curr_p, roi, achievement = "منتهي", 0.0, "⚪ انتهى العقد"
                except:
                    curr_p, roi, achievement = entry_price, 0.0, "🔄 جاري التحديث"

                rows_data.append({
                    "#": idx + 1,
                    "الوقت": row['Date'],
                    "العقد": f"{t_ticker} ${t_strike:g} {t_type}",
                    "الانتهاء": t_exp,
                    "سعر الدخول": f"${entry_price:.2f}",
                    "الهدف 1": f"${t1:.2f}",
                    "الهدف 2": f"${t2:.2f}",
                    "السعر الحالي": f"${curr_p:.2f}" if isinstance(curr_p, float) else curr_p,
                    "الربح/الخسارة": f"{roi:+.1f}%",
                    "الحالة": achievement
                })
            
            df_track = pd.DataFrame(rows_data)
            st.dataframe(df_track, hide_index=True, use_container_width=True)
            
            remove_num = st.selectbox("اختر رقم الصفقة لحذفها:", options=df_track["#"].tolist())
            if st.button("💔 إزالة من المفضلة"):
                log_df = log_df.drop(remove_num - 1).reset_index(drop=True)
                log_df.to_csv(LOG_FILE, index=False)
                st.rerun()
        else:
            st.info("لا توجد صفقات في المتابعة حالياً.")

    except Exception as e:
        st.error(f"حدث خطأ أثناء تحميل البيانات: {e}")
