import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import os

# 1. إعدادات الصفحة والستايل
st.set_page_config(page_title="Institutional GEX & Liquidity Hub", layout="wide")

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

st.title("⚡ منصة القاما والسيولة العمقية | GEX & Liquidity Hub")

LOG_FILE = "favorites_log.csv"
if not os.path.exists(LOG_FILE):
    df_empty = pd.DataFrame(columns=[
        "Date", "Ticker", "Type", "Strike", "Expiration", 
        "Entry_Contract_Price", "Target_1", "Target_2", "Stop_Loss"
    ])
    df_empty.to_csv(LOG_FILE, index=False)

def format_gex_val(val):
    abs_val = abs(val)
    if abs_val >= 1e9:
        return f"{val/1e9:.2f}B"
    elif abs_val >= 1e6:
        return f"{val/1e6:.1f}M"
    elif abs_val >= 1e3:
        return f"{val/1e3:.0f}K"
    else:
        return f"{val:.0f}"

# 2. القائمة الجانبية
st.sidebar.header("🎯 إعدادات السهم والتاريخ")
ticker_symbol = st.sidebar.text_input("رمز السهم", value="TSLA").upper()

if ticker_symbol:
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.fast_info
        
        price = info['lastPrice']
        prev_close = info['previousClose']
        change = price - prev_close
        pct_change = (change / prev_close) * 100
        
        all_expirations = stock.options

        target_expiration = None
        if all_expirations:
            target_expiration = st.sidebar.selectbox("اختر تاريخ الانتهاء المطلوب:", all_expirations)

        max_contract_price = st.sidebar.number_input("الحد الأقصى لسعر العقد ($)", value=1.50, step=0.10)

        # 3. جلب وحساب القاما والسيولة
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
            gex_merged = gex_merged.sort_values('strike').reset_index(drop=True)

            gex_near = gex_merged[(gex_merged['strike'] >= price * 0.85) & (gex_merged['strike'] <= price * 1.15)].copy()

            if not gex_near.empty:
                call_wall = gex_near.sort_values('Call_GEX', ascending=False).iloc[0]['strike']
                put_wall = gex_near.sort_values('Put_GEX', ascending=True).iloc[0]['strike']

                zero_cross = gex_near[gex_near['Net_GEX'] >= 0]
                if not zero_cross.empty:
                    gamma_flip = zero_cross.iloc[0]['strike']
                else:
                    gamma_flip = (call_wall + put_wall) / 2
            else:
                call_wall, put_wall, gamma_flip = price, price, price

            v_calls = c_df.groupby('strike')['volume'].sum().reset_index().rename(columns={'volume': 'Call_Vol'})
            v_puts = p_df.groupby('strike')['volume'].sum().reset_index().rename(columns={'volume': 'Put_Vol'})
            vol_merged = pd.merge(v_calls, v_puts, on='strike', how='outer').fillna(0)
            vol_near = vol_merged[(vol_merged['strike'] >= price * 0.90) & (vol_merged['strike'] <= price * 1.10)].sort_values('strike')

        else:
            call_wall, put_wall, gamma_flip = price, price, price
            call_ratio_pct = 50.0
            gex_near = pd.DataFrame()
            vol_near = pd.DataFrame()

        # 4. بطاقات القياس اللحظية
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"<div class='metric-card'><h4>السعر اللحظي</h4><h2>${price:.2f}</h2><p>{'🟢' if change>=0 else '🔴'} {change:+.2f} ({pct_change:+.2f}%)</p></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><h4>مستوى الفليب</h4><h2 style='color:#a371f7;'>${gamma_flip:.2f}</h2><p>Zero Gamma Flip</p></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><h4>(Call Wall) جدار القاما</h4><h2 style='color:#2ea043;'>${call_wall:g}</h2><p>هدف المقاومة/الرصد</p></div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div class='metric-card'><h4>(Put Wall) جدار البوت</h4><h2 style='color:#da3633;'>${put_wall:g}</h2><p>مستوى الدعم الرئيسي</p></div>", unsafe_allow_html=True)
        with col5:
            buyer_status = "سيطرة الشرائيين 🟢" if call_ratio_pct >= 50 else "سيطرة البائعين 🔴"
            st.markdown(f"<div class='metric-card'><h4>خلل التدفق (Call/Put Ratio)</h4><h2>{call_ratio_pct:.1f}%</h2><p>{buyer_status}</p></div>", unsafe_allow_html=True)

        st.divider()

        # 📈 5. شارت ATAS التفاعلي (شموع + فوليوم بروفايل جانبي + مستويات القاما)
        st.subheader(f"🖥️ شارت احترافي (نمط ATAS) - الفوليوم بروفايل ومستويات القاما ({ticker_symbol})")
        
        try:
            hist = yf.download(ticker_symbol, period="3m", interval="1d", progress=False)
            
            if not hist.empty:
                if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = hist.columns.get_level_values(0)
                
                # حساب Volume Profile برهن النطاقات السعرية
                num_bins = 40
                price_min = hist['Low'].min()
                price_max = hist['High'].max()
                bins = np.linspace(price_min, price_max, num_bins)
                
                # تجميع الفوليوم لكل مستوى سعري
                vol_profile = np.zeros(len(bins)-1)
                for idx, row in hist.iterrows():
                    # توزيع فوليوم اليوم على النطاق السعري لليوم
                    mask = (bins[:-1] >= row['Low']) & (bins[1:] <= row['High'])
                    if mask.sum() > 0:
                        vol_profile[mask] += row['Volume'] / mask.sum()
                    else:
                        vol_profile[0] += row['Volume']

                bin_centers = (bins[:-1] + bins[1:]) / 2

                # إنشاء Subplot بثلاث شبكات: 1) شارت الشموع 2) شارت الفوليوم بروفايل الجانبي
                fig_atas = make_subplots(
                    rows=2, cols=2,
                    column_widths=[0.8, 0.2],
                    row_heights=[0.8, 0.2],
                    shared_yaxes=True,
                    horizontal_spacing=0.02,
                    vertical_spacing=0.03,
                    specs=[[{"type": "candlestick"}, {"type": "bar"}],
                           [{"type": "bar"}, None]]
                )

                # 1. شارت الشموع الرئيسي (Main Candlestick)
                fig_atas.add_trace(go.Candlestick(
                    x=hist.index,
                    open=hist['Open'],
                    high=hist['High'],
                    low=hist['Low'],
                    close=hist['Close'],
                    name="السعر",
                    increasing_line_color='#2ea043',
                    decreasing_line_color='#da3633'
                ), row=1, col=1)

                # 2. الفوليوم اليومي في الجزء السفلي
                colors_vol = ['#2ea043' if c >= o else '#da3633' for c, o in zip(hist['Close'], hist['Open'])]
                fig_atas.add_trace(go.Bar(
                    x=hist.index,
                    y=hist['Volume'],
                    marker_color=colors_vol,
                    name="الحجم اليومي",
                    showlegend=False
                ), row=2, col=1)

                # 3. الفوليوم بروفايل الجانبي (Volume Profile - ATAS Style)
                fig_atas.add_trace(go.Bar(
                    x=vol_profile,
                    y=bin_centers,
                    orientation='h',
                    marker=dict(
                        color='rgba(31, 111, 235, 0.45)',
                        line=dict(color='#1f6feb', width=1)
                    ),
                    name="Volume Profile",
                    showlegend=False
                ), row=1, col=2)

                # إضافة خطوط القاما على شارت السعر الرئيسي
                fig_atas.add_hline(y=gamma_flip, line_dash="dash", line_color="#a371f7", line_width=2,
                                  annotation_text=f"Gamma Flip (${gamma_flip:.2f})", annotation_position="top left", row=1, col=1)
                fig_atas.add_hline(y=call_wall, line_dash="dot", line_color="#2ea043", line_width=2,
                                  annotation_text=f"Call Wall (${call_wall:g})", annotation_position="top left", row=1, col=1)
                fig_atas.add_hline(y=put_wall, line_dash="dot", line_color="#da3633", line_width=2,
                                  annotation_text=f"Put Wall (${put_wall:g})", annotation_position="bottom left", row=1, col=1)

                # إعدادات التنسيق والهيكل (ATAS Theme)
                fig_atas.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="#080a0f",
                    plot_bgcolor="#0e121b",
                    xaxis_rangeslider_visible=False,
                    xaxis2_rangeslider_visible=False,
                    margin=dict(l=10, r=10, t=30, b=10),
                    height=520,
                    showlegend=False
                )
                
                fig_atas.update_xaxes(gridcolor='#1b2230', row=1, col=1)
                fig_atas.update_yaxes(gridcolor='#1b2230', row=1, col=1)
                fig_atas.update_xaxes(visible=False, row=1, col=2) # إخفاء محور سين الفوليوم الجانبي للنظافة

                st.plotly_chart(fig_atas, use_container_width=True)
            else:
                st.warning("⚠️ تعذر جلب الشموع اليابانية لهذا السهم حالياً من المصدر.")
        except Exception as chart_err:
            st.error(f"⚠️ خطأ أثناء عرض الشارت الاحترافي: {chart_err}")

        st.divider()

        # 6. عرض شارت Net GEX
        st.subheader(f"📊 شارت القاما الصافية (Net GEX) - الانتهاء: [{target_expiration}]")

        if not gex_near.empty and gex_near['Net_GEX'].abs().sum() > 0:
            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_facecolor('#080a0f')
            ax.set_facecolor('#0e121b')

            colors = ['#2ea043' if val >= 0 else '#da3633' for val in gex_near['Net_GEX']]
            bars = ax.barh(gex_near['strike'], gex_near['Net_GEX'], color=colors, height=0.6)

            max_abs_gex = gex_near['Net_GEX'].abs().max()
            for bar, val in zip(bars, gex_near['Net_GEX']):
                if abs(val) > 0:
                    text_x = bar.get_width()
                    ha = 'left' if text_x >= 0 else 'right'
                    offset = (max_abs_gex * 0.015) if text_x >= 0 else -(max_abs_gex * 0.015)
                    ax.text(text_x + offset, bar.get_y() + bar.get_height()/2, format_gex_val(val),
                            va='center', ha=ha, color='#ffffff', fontsize=8, fontweight='bold')

            ax.axhline(price, color='#38d430', linestyle='--', linewidth=2, label=f'السعر الحالي (${price:.2f})')
            ax.axhline(gamma_flip, color='#a371f7', linestyle=':', linewidth=2, label=f'Gamma Flip (${gamma_flip:.2f})')

            ax.set_ylabel('سعر الإضراب Strike ($)', color='#e1e4e8', fontsize=11)
            ax.set_xlabel('صافي القاما Net GEX ($)', color='#e1e4e8', fontsize=11)
            ax.tick_params(colors='#e1e4e8')
            ax.grid(color='#1b2230', linestyle='--', alpha=0.5)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: format_gex_val(x)))
            ax.legend(facecolor='#0e121b', edgecolor='#232a3b', labelcolor='#e1e4e8')

            st.pyplot(fig)
        else:
            st.warning("⚠️ لا توجد بيانات قاما كافية للتاريخ المحدد.")

        st.divider()

        # 7. شارت عمق السيولة
        st.subheader(f"📊 عمق السيولة وتوزيع الفوليوم ({ticker_symbol})")
        if not vol_near.empty:
            fig_vol, ax_v = plt.subplots(figsize=(10, 4.5))
            fig_vol.patch.set_facecolor('#080a0f')
            ax_v.set_facecolor('#0e121b')

            strikes = vol_near['strike'].tolist()
            c_v = vol_near['Call_Vol'].tolist()
            p_v = vol_near['Put_Vol'].tolist()

            ax_v.bar(strikes, c_v, color='#1f6feb', width=1.2, label='سيولة الكول (Call Vol)')
            ax_v.bar(strikes, p_v, bottom=c_v, color='#388bfd', alpha=0.6, width=1.2, label='سيولة البوت (Put Vol)')

            ax_v.set_ylabel('حجم العقود', color='#e1e4e8', fontsize=10)
            ax_v.set_xlabel('سعر الإضراب Strike ($)', color='#e1e4e8', fontsize=10)
            ax_v.tick_params(colors='#e1e4e8')
            ax_v.grid(color='#1b2230', linestyle='--', alpha=0.4)
            ax_v.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"{int(x/1000)}K" if x>=1000 else f"{int(x)}"))
            ax_v.legend(facecolor='#0e121b', edgecolor='#232a3b', labelcolor='#e1e4e8')

            st.pyplot(fig_vol)

        st.divider()

        # 8. التوصية الفورية + سبب الاختيار
        st.subheader("🎯 التوصية الفورية")
        signal_type = "NEUTRAL"
        reason_text = ""

        if price > gamma_flip:
            signal_type = "CALL"
            reason_text = f"السعر اللحظي (${price:.2f}) أعلى من مستوى الفليب Gamma Flip (${gamma_flip:.2f}) مما يدعم استمرار الزخم الصعودي وتفوق سيطرة الشرائيين."
        elif price < gamma_flip:
            signal_type = "PUT"
            reason_text = f"السعر اللحظي (${price:.2f}) أدنى من مستوى الفليب Gamma Flip (${gamma_flip:.2f}) مما يعزز الضغط البيعي ويتجه نحو مستويات الدعم."

        if target_expiration and signal_type != "NEUTRAL":
            opt = stock.option_chain(target_expiration)
            chain = opt.calls if signal_type == "CALL" else opt.puts
            chain['Trade_Value'] = chain['volume'] * chain['lastPrice'] * 100
            
            valid = chain[(chain['lastPrice'] <= max_contract_price) & (chain['lastPrice'] >= 0.20)]
            
            selected_contract = None
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
                    <h3>🏆 فرصة فورية (إشارة دخول) - {ticker_symbol} - ${strike_price:g} {c_type}</h3>
                    <p><b>تاريخ الانتهاء:</b> {target_expiration} | <b>سعر العقد:</b> <span style='color:#f0883e; font-size:1.3em;'>${contract_price:.2f}</span> (${contract_price*100:.0f} لكل عقد)</p>
                    <p style='background-color: #161b22; padding: 10px; border-radius: 8px; border-right: 4px solid #58a6ff;'>
                        📌 <b>سبب اختيار التوصية:</b> {reason_text}
                    </p>
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
                        "Expiration": target_expiration,
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

        # 9. جدول المتابعة
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
