import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os

# 1. تهيئة الصفحة والستايل المتجاوب مع الجوال
st.set_page_config(page_title="Alpha Capital | Institutional Options Terminal", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background-color: #06080c; color: #f0f6fc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    
    .gold-header {
        background: linear-gradient(90deg, #d4af37, #f3e5ab, #aa771c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 1.8rem;
    }
    
    .hero-card {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 16px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    }
    
    .trade-card-call {
        background: linear-gradient(135deg, #062b16 0%, #0d4429 100%);
        border: 2px solid #2ea043;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 10px 30px rgba(46, 160, 67, 0.2);
    }
    
    .trade-card-put {
        background: linear-gradient(135deg, #3c0d12 0%, #67161d 100%);
        border: 2px solid #da3633;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 10px 30px rgba(218, 54, 51, 0.2);
    }

    .wait-card {
        background: linear-gradient(135deg, #271d0c 0%, #433013 100%);
        border: 2px solid #d29922;
        border-radius: 16px;
        padding: 20px;
    }

    .stat-badge {
        background-color: #21262d;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 0.85em;
        border: 1px solid #30363d;
        text-align: center;
        flex: 1;
        min-width: 90px;
    }

    /* تحسين التصميم للشاشات الصغيرة والجوالات */
    @media (max-width: 768px) {
        .gold-header { font-size: 1.3rem; }
        .hero-flex { flex-direction: column !important; align-items: flex-start !important; gap: 12px; }
        .badges-flex { width: 100%; justify-content: space-between; }
        .grid-targets { grid-template-columns: repeat(2, 1fr) !important; }
    }
    </style>
""", unsafe_allow_html=True)

# 2. إدارة ملف السجل وتفادي KeyError تلقائياً
LOG_FILE = "favorites_log.csv"
REQUIRED_COLUMNS = [
    "Date", "Ticker", "Type", "Strike", "Expiration", 
    "Entry_Price", "Target_1", "Target_2", "Target_3", "Stop_Loss", "Contracts"
]

def load_favorites():
    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        df.to_csv(LOG_FILE, index=False)
        return df
    try:
        df = pd.read_csv(LOG_FILE)
        # التحقق من وجود جميع الأعمدة المطلوبة
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = np.nan
        return df[REQUIRED_COLUMNS]
    except Exception:
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        df.to_csv(LOG_FILE, index=False)
        return df

# 3. الهيدر الرئيسي
st.markdown("<h1 class='gold-header'>💎 ALPHA CAPITAL | المنصة الرقمية للتداول المؤسسي</h1>", unsafe_allow_html=True)
st.caption("🚀 محرك الخوارزميات المتقدم لاقتناص العقود مرتفعة الانفجار وحماية المحفظة")

# 4. القائمة الجانبية (شريط التحكم وإدارة رأس المال)
st.sidebar.markdown("### ⚙️ إدارة الحساب ورأس المال")
portfolio_size = st.sidebar.number_input("إجمالي رأس المال المخصص ($)", value=2000, step=250)
risk_per_trade_pct = st.sidebar.slider("نسبة المخاطرة القصوى للصفقة (%)", min_value=5, max_value=25, value=10)

max_trade_budget = portfolio_size * (risk_per_trade_pct / 100.0)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 تحديد السهم والمُهل")
ticker_symbol = st.sidebar.text_input("رمز السهم (Ticker)", value="NVDA").strip().upper()

if ticker_symbol:
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.fast_info
        
        price = info['lastPrice']
        prev_close = info['previousClose']
        change = price - prev_close
        pct_change = (change / prev_close) * 100
        
        all_expirations = stock.options

        if all_expirations:
            target_expiration = st.sidebar.selectbox("📅 اختر تاريخ انتهاء العقد:", all_expirations)
        else:
            target_expiration = None

        max_contract_price = st.sidebar.number_input("أقصى سعر للعقد المفرد ($)", value=2.00, step=0.10)

        # 5. تحليل السيولة وصافي القاما (GEX)
        if target_expiration:
            opt = stock.option_chain(target_expiration)
            c_df, p_df = opt.calls.copy(), opt.puts.copy()

            c_vol_total = c_df['volume'].fillna(0).sum()
            p_vol_total = p_df['volume'].fillna(0).sum()
            total_vol = c_vol_total + p_vol_total
            call_ratio_pct = (c_vol_total / total_vol * 100) if total_vol > 0 else 50.0

            c_oi = c_df['openInterest'].fillna(0)
            p_oi = p_df['openInterest'].fillna(0)
            if c_oi.sum() == 0: c_oi = c_df['volume'].fillna(0)
            if p_oi.sum() == 0: p_oi = p_df['volume'].fillna(0)

            c_df['Call_GEX'] = c_oi * c_df['impliedVolatility'].fillna(0.2) * (price**2) * 0.01
            p_df['Put_GEX'] = -p_oi * p_df['impliedVolatility'].fillna(0.2) * (price**2) * 0.01

            gex_calls = c_df.groupby('strike')['Call_GEX'].sum().reset_index()
            gex_puts = p_df.groupby('strike')['Put_GEX'].sum().reset_index()

            gex_merged = pd.merge(gex_calls, gex_puts, on='strike', how='outer').fillna(0)
            gex_merged['Net_GEX'] = gex_merged['Call_GEX'] + gex_merged['Put_GEX']
            
            gex_near = gex_merged[(gex_merged['strike'] >= price * 0.85) & (gex_merged['strike'] <= price * 1.15)].copy()

            if not gex_near.empty:
                call_wall = gex_near.sort_values('Call_GEX', ascending=False).iloc[0]['strike']
                put_wall = gex_near.sort_values('Put_GEX', ascending=True).iloc[0]['strike']
                zero_cross = gex_near[gex_near['Net_GEX'] >= 0]
                gamma_flip = zero_cross.iloc[0]['strike'] if not zero_cross.empty else (call_wall + put_wall) / 2
            else:
                call_wall, put_wall, gamma_flip = price, price, price
        else:
            call_wall, put_wall, gamma_flip = price, price, price
            call_ratio_pct = 50.0

        # 6. لوحة مؤشرات الأداء الحية (متجاوبة مع الجوال)
        st.markdown(f"""
        <div class='hero-card'>
            <div class='hero-flex' style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <h3 style='margin:0; font-size:1.4em;'>{ticker_symbol} <span style='font-size:0.6em; color:#8b949e;'>السعر اللحظي</span></h3>
                    <h1 style='margin:0; font-size: 2.2em; color:#ffffff;'>${price:.2f} 
                        <span style='font-size:0.5em; color:{'#2ea043' if change>=0 else '#da3633'};'>({change:+.2f} / {pct_change:+.2f}%)</span>
                    </h1>
                </div>
                <div class='badges-flex' style='display:flex; gap:8px;'>
                    <div class='stat-badge'><b>Zero Gamma:</b><br><span style='color:#a371f7; font-weight:bold;'>${gamma_flip:.2f}</span></div>
                    <div class='stat-badge'><b>Call Wall:</b><br><span style='color:#2ea043; font-weight:bold;'>${call_wall:g}</span></div>
                    <div class='stat-badge'><b>Put Wall:</b><br><span style='color:#da3633; font-weight:bold;'>${put_wall:g}</span></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 7. التقييم الخوارزمي والتوصية الذكية
        signal_type = "NEUTRAL"
        confidence_score = 0

        dist_from_flip = ((price - gamma_flip) / gamma_flip) * 100

        if price > gamma_flip and call_ratio_pct >= 52:
            signal_type = "CALL"
            confidence_score = min(98, int(60 + abs(dist_from_flip)*5 + (call_ratio_pct - 50)))
        elif price < gamma_flip and call_ratio_pct <= 48:
            signal_type = "PUT"
            confidence_score = min(98, int(60 + abs(dist_from_flip)*5 + (50 - call_ratio_pct)))
        
        if target_expiration and signal_type != "NEUTRAL":
            opt = stock.option_chain(target_expiration)
            chain = opt.calls if signal_type == "CALL" else opt.puts
            chain['Liquidity_Score'] = chain['volume'].fillna(0) * chain['openInterest'].fillna(0)
            
            valid = chain[(chain['lastPrice'] <= max_contract_price) & (chain['lastPrice'] >= 0.15)]
            
            if not valid.empty:
                selected_contract = valid.sort_values('Liquidity_Score', ascending=False).iloc[0]
                strike_price = selected_contract['strike']
                contract_price = selected_contract['lastPrice']
                single_contract_cost = contract_price * 100
                
                recommended_contracts = max(1, int(max_trade_budget // single_contract_cost))
                total_position_cost = recommended_contracts * single_contract_cost

                target_1 = contract_price * 1.20   # (+20%)
                target_2 = contract_price * 1.45   # (+45%)
                target_3 = contract_price * 2.00   # (+100%)
                stop_loss = contract_price * 0.82  # (-18%)

                card_style = "trade-card-call" if signal_type == "CALL" else "trade-card-put"
                badge_color = "#2ea043" if signal_type == "CALL" else "#da3633"

                st.markdown(f"""
                <div class='{card_style}'>
                    <div style='display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;'>
                        <span style='background-color:{badge_color}; color:#fff; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:0.9em;'>
                            إشارة دخول 🔥 {signal_type}
                        </span>
                        <span style='color:#e1e4e8; font-size:0.9em;'>نسبة الثقة: <b style='color:#f0883e;'>{confidence_score}%</b></span>
                    </div>
                    
                    <h3 style='margin-top:12px; font-size:1.6em;'>{ticker_symbol} - Strike ${strike_price:g} {signal_type}</h3>
                    <p style='font-size:0.95em;'>📅 <b>الانتهاء:</b> {target_expiration} | <b>سعر العقد:</b> <span style='color:#f0883e; font-weight:bold;'>${contract_price:.2f}</span></p>

                    <div style='background-color:rgba(0,0,0,0.3); padding:12px; border-radius:10px; margin:12px 0;'>
                        <h5 style='margin:0 0 6px 0; color:#58a6ff;'>🧮 إدارة المركز:</h5>
                        <p style='margin:2px 0; font-size:0.9em;'>• <b>عدد العقود:</b> <span style='color:#ffffff; font-weight:bold;'>{recommended_contracts} عقود</span></p>
                        <p style='margin:2px 0; font-size:0.9em;'>• <b>التكلفة:</b> <span style='color:#ffffff; font-weight:bold;'>${total_position_cost:.2f}</span> ({ (total_position_cost/portfolio_size)*100:.1f}% من المحفظة)</p>
                    </div>

                    <div class='grid-targets' style='display: grid; grid-template-columns: repeat(4, 1fr); gap:8px; text-align:center;'>
                        <div style='background:rgba(255,255,255,0.05); padding:8px; border-radius:8px;'>
                            <small style='color:#8b949e; font-size:0.75em;'>🎯 خاطف (+20%)</small>
                            <h4 style='color:#2ea043; margin:2px 0;'>${target_1:.2f}</h4>
                        </div>
                        <div style='background:rgba(255,255,255,0.05); padding:8px; border-radius:8px;'>
                            <small style='color:#8b949e; font-size:0.75em;'>🚀 أساسي (+45%)</small>
                            <h4 style='color:#388bfd; margin:2px 0;'>${target_2:.2f}</h4>
                        </div>
                        <div style='background:rgba(255,255,255,0.05); padding:8px; border-radius:8px;'>
                            <small style='color:#8b949e; font-size:0.75em;'>💎 امتدادي (+100%)</small>
                            <h4 style='color:#a371f7; margin:2px 0;'>${target_3:.2f}</h4>
                        </div>
                        <div style='background:rgba(255,255,255,0.05); padding:8px; border-radius:8px;'>
                            <small style='color:#8b949e; font-size:0.75em;'>🛑 الوقف (-18%)</small>
                            <h4 style='color:#da3633; margin:2px 0;'>${stop_loss:.2f}</h4>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                if st.button("💖 إضافة الصفقة إلى قائمة المتابعة الحية", use_container_width=True):
                    log_df = load_favorites()
                    new_row = {
                        "Date": datetime.now().strftime('%m-%d %H:%M'),
                        "Ticker": ticker_symbol,
                        "Type": signal_type,
                        "Strike": strike_price,
                        "Expiration": target_expiration,
                        "Entry_Price": contract_price,
                        "Target_1": target_1,
                        "Target_2": target_2,
                        "Target_3": target_3,
                        "Stop_Loss": stop_loss,
                        "Contracts": recommended_contracts
                    }
                    log_df = pd.concat([log_df, pd.DataFrame([new_row])], ignore_index=True)
                    log_df.to_csv(LOG_FILE, index=False)
                    st.success("تم تثبيت الصفقة في القائمة المباشرة! 💖")
                    st.rerun()
            else:
                st.warning("⚠️ لا توجد عقود تطابق شروط السعر أو السيولة في التاريخ المحدد.")
        else:
            st.markdown("""
            <div class='wait-card'>
                <h3 style='color:#d29922; margin:0;'>🛑 قرار الخوارزمية: الانتظار وتجميد التداول (Hold Cash)</h3>
                <p style='font-size:0.95em; margin-top:8px;'>السعر حالياً يدور في منطقة تذبذب ضيقة بالقرب من Gamma Flip ولا توجد غلبة واضحة للشرائيين أو البائعين. لحماية رأس المال، نوصي بعدم الدخول الآن.</p>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # 8. جدول الصفقات المفتوحة والمتابعة الحية
        st.markdown("### 📋 الصفقات المفتوحة والمتابعة الحية")
        log_df = load_favorites()
        
        # تنظيف الصفوف الفارغة إن وجدت
        log_df = log_df.dropna(subset=['Ticker', 'Entry_Price'])

        if not log_df.empty:
            rows_data = []
            for idx, row in log_df.iterrows():
                t_ticker = str(row['Ticker'])
                t_strike = float(row['Strike'])
                t_type = str(row['Type'])
                t_exp = str(row['Expiration'])
                entry_p = float(row['Entry_Price']) if pd.notnull(row['Entry_Price']) else 0.0
                t1 = float(row['Target_1']) if pd.notnull(row['Target_1']) else 0.0
                t2 = float(row['Target_2']) if pd.notnull(row['Target_2']) else 0.0
                t3 = float(row['Target_3']) if pd.notnull(row['Target_3']) else 0.0
                sl = float(row['Stop_Loss']) if pd.notnull(row['Stop_Loss']) else 0.0
                num_c = float(row['Contracts']) if pd.notnull(row['Contracts']) else 1.0
                
                try:
                    s_ticker = yf.Ticker(t_ticker)
                    s_opt = s_ticker.option_chain(t_exp)
                    chain = s_opt.calls if t_type == "CALL" else s_opt.puts
                    matched = chain[chain['strike'] == t_strike]
                    
                    if not matched.empty:
                        curr_p = float(matched['lastPrice'].values[0])
                        roi = ((curr_p - entry_p) / entry_p) * 100 if entry_p > 0 else 0.0
                        pnl_usd = (curr_p - entry_p) * 100 * num_c
                        
                        if curr_p >= t3: status = "💎 تم تحضير +100%"
                        elif curr_p >= t2: status = "🚀 تحقق الهدف 2"
                        elif curr_p >= t1: status = "🎯 تحقق الهدف 1"
                        elif curr_p <= sl: status = "🛑 ضرب وقف الخسارة"
                        else: status = "⏳ قيد التداول"
                    else:
                        curr_p, roi, pnl_usd, status = entry_p, 0.0, 0.0, "⚪ انتهى العقد"
                except Exception:
                    curr_p, roi, pnl_usd, status = entry_p, 0.0, 0.0, "🔄 تحديث"

                rows_data.append({
                    "#": idx + 1,
                    "التاريخ": row['Date'],
                    "الصفقة": f"{t_ticker} ${t_strike:g} {t_type}",
                    "الانتهاء": t_exp,
                    "العقود": int(num_c),
                    "سعر الدخول": f"${entry_p:.2f}",
                    "السعر اللحظي": f"${curr_p:.2f}" if isinstance(curr_p, float) else curr_p,
                    "العائد (%)": f"{roi:+.1f}%",
                    "الربح/الخسارة ($)": f"${pnl_usd:+.2f}",
                    "الحالة": status
                })
            
            df_track = pd.DataFrame(rows_data)
            st.dataframe(df_track, hide_index=True, use_container_width=True)
            
            col_del1, col_del2 = st.columns([3, 1])
            with col_del1:
                remove_num = st.selectbox("اختر رقم الصفقة لحذفها عند الإغلاق:", options=df_track["#"].tolist())
            with col_del2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ إغلاق وحذف الصفقة"):
                    log_df = log_df.drop(remove_num - 1).reset_index(drop=True)
                    log_df.to_csv(LOG_FILE, index=False)
                    st.success("تم إغلاق الصفقة وحذفها.")
                    st.rerun()
        else:
            st.info("لا توجد صفقات مفتوحة حالياً في قائمة المتابعة.")

    except Exception as e:
        st.error(f"حدث خطأ أثناء تحميل البيانات: {e}")
