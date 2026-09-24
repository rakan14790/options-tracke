import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os

# 1. إعدادات الصفحة والستايل
st.set_page_config(page_title="NVDA GEX & Volume Hub", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #080a0f; color: #e1e4e8; }
    .metric-card {
        background: linear-gradient(145deg, #0e121b, #151a26);
        border: 1px solid #232a3b;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
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

st.title("⚡ محرك القاما المطور والسيولة | Multi-Expiration Net GEX")

LOG_FILE = "favorites_log.csv"
if not os.path.exists(LOG_FILE):
    df_empty = pd.DataFrame(columns=[
        "Date", "Ticker", "Type", "Strike", "Expiration", 
        "Entry_Contract_Price", "Target_1", "Target_2", "Stop_Loss"
    ])
    df_empty.to_csv(LOG_FILE, index=False)

# 2. القائمة الجانبية وتصفية تواريخ الانتهاء
st.sidebar.header("🎯 إعدادات السهم وتصفية العقود")
ticker_symbol = st.sidebar.text_input("رمز السهم", value="NVDA").upper()

if ticker_symbol:
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.fast_info
        
        price = info['lastPrice']
        prev_close = info['previousClose']
        change = price - prev_close
        pct_change = (change / prev_close) * 100
        
        all_expirations = stock.options

        # قائمة خيارات تصفية التواريخ
        exp_mode = st.sidebar.radio(
            "اختر نوع القاما المراد عرضها:",
            ["اليومية (أقرب انتهاء 0DTE/أسبوعي)", "تحديد انتهاء محدد (أربعاء / جمعة)", "دمج جميع التواريخ المتاحة (All Combined)"]
        )

        selected_expirations = []

        if exp_mode == "اليومية (أقرب انتهاء 0DTE/أسبوعي)":
            if all_expirations:
                selected_expirations = [all_expirations[0]]
        elif exp_mode == "دمج جميع التواريخ المتاحة (All Combined)":
            selected_expirations = list(all_expirations[:6]) # دمج أول 6 تواريخ لتفادي بطء التحميل
        else:
            # تصفية العقود حسب يوم الأسبوع (الأربعاء = 2، الجمعة = 4)
            weekday_choice = st.sidebar.selectbox("اختر اليوم المستهدف:", ["الجمعة فقط (Fridays)", "الأربعاء فقط (Wednesdays)"])
            target_day = 4 if "الجمعة" in weekday_choice else 2
            
            for exp in all_expirations:
                exp_dt = datetime.strptime(exp, "%Y-%m-%d")
                if exp_dt.weekday() == target_day:
                    selected_expirations.append(exp)
            
            if selected_expirations:
                chosen_specific = st.sidebar.selectbox("اختر تاريخ الانتهاء المحدد:", selected_expirations)
                selected_expirations = [chosen_specific]

        max_contract_price = st.sidebar.number_input("الحد الأقصى لسعر العقد ($)", value=1.50, step=0.10)

        # 3. تجميع وحساب القاما الصافية Net GEX
        combined_calls = []
        combined_puts = []

        for exp in selected_expirations:
            try:
                opt = stock.option_chain(exp)
                c, p = opt.calls.copy(), opt.puts.copy()
                c['expiration'] = exp
                p['expiration'] = exp
                combined_calls.append(c)
                combined_puts.append(p)
            except:
                continue

        if combined_calls and combined_puts:
            calls_df = pd.concat(combined_calls, ignore_index=True)
            puts_df = pd.concat(combined_puts, ignore_index=True)

            calls_df['Call_GEX'] = calls_df['volume'].fillna(0) * calls_df['impliedVolatility'].fillna(0.2) * price * 0.01
            puts_df['Put_GEX'] = -puts_df['volume'].fillna(0) * puts_df['impliedVolatility'].fillna(0.2) * price * 0.01

            # تجميع القاما حسب السترايك
            gex_calls = calls_df.groupby('strike')['Call_GEX'].sum().reset_index()
            gex_puts = puts_df.groupby('strike')['Put_GEX'].sum().reset_index()

            gex_merged = pd.merge(gex_calls, gex_puts, on='strike', how='outer').fillna(0)
            gex_merged['Net_GEX'] = gex_merged['Call_GEX'] + gex_merged['Put_GEX']

            # تصفية السترايكات القريبة من السعر الحالي (±10%)
            gex_near = gex_merged[(gex_merged['strike'] >= price * 0.90) & (gex_merged['strike'] <= price * 1.10)].sort_values('strike')

            call_wall = gex_near.sort_values('Call_GEX', ascending=False).iloc[0]['strike'] if not gex_near.empty else price
            put_wall = gex_near.sort_values('Put_GEX', ascending=True).iloc[0]['strike'] if not gex_near.empty else price
            gamma_flip = (call_wall + put_wall) / 2
        else:
            call_wall, put_wall, gamma_flip = price, price, price
            gex_near = pd.DataFrame()

        # 4. عرض البطاقات الرقمية
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"<div class='metric-card'><h4>السعر اللحظي (Spot Price)</h4><h2>${price:.2f}</h2><p>{'🟢' if change>=0 else '🔴'} {change:+.2f} ({pct_change:+.2f}%)</p></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><h4>مستوى الفليب (Gamma Flip)</h4><h2 style='color:#a371f7;'>${gamma_flip:.2f}</h2><p>نقطة تحول الزخم</p></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><h4>جدار الكول (Call Wall)</h4><h2 style='color:#2ea043;'>${call_wall:g}</h2><p>أعلى قاما إيجابية</p></div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div class='metric-card'><h4>جدار البوت (Put Wall)</h4><h2 style='color:#da3633;'>${put_wall:g}</h2><p>أعلى قاما سلبية</p></div>", unsafe_allow_html=True)

        st.divider()

        # 5. عرض شارت Net GEX المبسط والواضح
        exp_label = ", ".join(selected_expirations) if len(selected_expirations) <= 2 else f"مدمج ({len(selected_expirations)} تواريخ)"
        st.subheader(f"📊 شارت القاما الصافية المبسط (Net GEX) - العقود المستهدفة: [{exp_label}]")

        if not gex_near.empty:
            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_facecolor('#080a0f')
            ax.set_facecolor('#0e121b')

            colors = ['#2ea043' if val >= 0 else '#da3633' for val in gex_near['Net_GEX']]
            ax.barh(gex_near['strike'], gex_near['Net_GEX'], color=colors, height=0.7)

            ax.axhline(price, color='#38d430', linestyle='--', linewidth=2, label=f'السعر الحالي (${price:.2f})')
            ax.axhline(gamma_flip, color='#a371f7', linestyle=':', linewidth=2, label=f'Gamma Flip (${gamma_flip:.2f})')

            ax.set_ylabel('سعر الإضراب Strike ($)', color='#e1e4e8', fontsize=11)
            ax.set_xlabel('صافي القاما (Net GEX Magnitude)', color='#e1e4e8', fontsize=11)
            ax.tick_params(colors='#e1e4e8')
            ax.grid(color='#1b2230', linestyle='--', alpha=0.5)
            ax.legend(facecolor='#0e121b', edgecolor='#232a3b', labelcolor='#e1e4e8')

            st.pyplot(fig)

        st.divider()

        # 6. الفوليوم بروفايل اليومي
        st.subheader(f"📈 الفوليوم بروفايل اليومي | Daily Volume Profile ({ticker_symbol})")
        hist = stock.history(period="1mo", interval="1d")
        if not hist.empty:
            num_bins = 30
            price_bins = np.linspace(hist['Low'].min(), hist['High'].max(), num_bins)
            hist['Bin'] = pd.cut(hist['Close'], bins=price_bins)
            vol_profile = hist.groupby('Bin', observed=False)['Volume'].sum().reset_index()
            
            poc_row = vol_profile.loc[vol_profile['Volume'].idxmax()]
            poc_price = (poc_row['Bin'].left + poc_row['Bin'].right) / 2
            
            fig_vp, ax_vp = plt.subplots(figsize=(10, 3.5))
            fig_vp.patch.set_facecolor('#080a0f')
            ax_vp.set_facecolor('#0e121b')

            ax_vp.plot(hist.index, hist['Close'], color='#58a6ff', label='السعر اليومي', linewidth=1.5)
            ax_vp.axhline(poc_price, color='#f0883e', linestyle='--', linewidth=2, label=f'POC اليومي: ${poc_price:.2f}')
            ax_vp.axhline(price, color='#38d430', linestyle=':', label=f'السعر الحالي: ${price:.2f}')

            ax_vp.set_ylabel('السعر ($)', color='#e1e4e8')
            ax_vp.tick_params(colors='#e1e4e8')
            ax_vp.grid(color='#1b2230', linestyle='--', alpha=0.5)
            ax_vp.legend(facecolor='#0e121b', edgecolor='#232a3b', labelcolor='#e1e4e8')

            st.pyplot(fig_vp)

        st.divider()

        # 7. التوصية الفورية وتجهيز الصفقة
        st.subheader("🎯 التوصية الفورية")
        signal_type = "NEUTRAL"
        if price > gamma_flip:
            signal_type = "CALL"
        elif price < gamma_flip:
            signal_type = "PUT"

        if selected_expirations and signal_type != "NEUTRAL":
            target_exp = selected_expirations[0]
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
                
                target_1 = contract_price * 1.25
                target_2 = contract_price * 1.50
                stop_loss = contract_price * 0.85
                
                st.markdown(f"""
                <div class='recommendation-box'>
                    <h3>🏆 فرصة درجة (+A) على أسهم {ticker_symbol} - ${strike_price:g} {c_type}</h3>
                    <p><b>تاريخ الانتهاء:</b> {target_exp} | <b>سعر الدخول:</b> <span style='color:#f0883e; font-size:1.3em;'>${contract_price:.2f}</span> (${contract_price*100:.0f} للعقد)</p>
                    <p style='color:#8b949e;'>💡 <b>السبب الفني:</b> التداول أعلى مستوى Gamma Flip (${gamma_flip:.2f}) والمحدد بناءً على فلتر العقود المختارة.</p>
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
                <p>السهم في نطاق محايد حول Gamma Flip. يفضل الانتظار للحفاظ على رأس المال.</p>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # 8. جدول المتابعة
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
