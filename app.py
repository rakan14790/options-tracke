import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

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

    @media (max-width: 768px) {
        .gold-header { font-size: 1.3rem; }
        .hero-flex { flex-direction: column !important; align-items: flex-start !important; gap: 12px; }
        .badges-flex { width: 100%; justify-content: space-between; }
        .grid-targets { grid-template-columns: repeat(2, 1fr) !important; }
    }
    </style>
""", unsafe_allow_html=True)

# الهيدر الرئيسي
st.markdown("<h1 class='gold-header'>💎 ALPHA CAPITAL | المنصة الرقمية للتداول المؤسسي</h1>", unsafe_allow_html=True)
st.caption("🚀 محرك الخوارزميات المتقدم لاقتناص العقود مرتفعة الانفجار وتحليل سيولة الخيارات")

# 2. إعدادات السهم الجانبية
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
        target_expiration = st.sidebar.selectbox("📅 اختر تاريخ انتهاء العقد:", all_expirations) if all_expirations else None

        # تحليل القاما والسيولة (GEX)
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

        # عرض الأسعار ومستويات القاما
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

        # التقييم الخوارزمي والتوصية
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
            
            valid = chain[(chain['lastPrice'] >= 0.15)]
            if not valid.empty:
                selected_contract = valid.sort_values('Liquidity_Score', ascending=False).iloc[0]
                strike_price = selected_contract['strike']
                contract_price = selected_contract['lastPrice']

                target_1 = contract_price * 1.20
                target_2 = contract_price * 1.45
                target_3 = contract_price * 2.00
                stop_loss = contract_price * 0.82

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
                    <p style='font-size:0.95em;'>📅 <b>الانتهاء:</b> {target_expiration} | <b>سعر العقد المقترح:</b> <span style='color:#f0883e; font-weight:bold;'>${contract_price:.2f}</span></p>

                    <div class='grid-targets' style='display: grid; grid-template-columns: repeat(4, 1fr); gap:8px; text-align:center; margin-top:12px;'>
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
        else:
            st.markdown("""
            <div class='wait-card'>
                <h3 style='color:#d29922; margin:0;'>🛑 قرار الخوارزمية: الانتظار وتجميد التداول (Hold Cash)</h3>
                <p style='font-size:0.95em; margin-top:8px;'>السعر حالياً يدور في منطقة تذبذب ضيقة بالقرب من Gamma Flip ولا توجد غلبة واضحة للشرائيين أو البائعين.</p>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # 3. شارت القاما الصافية (Net GEX Chart) باستخدام Plotly
        st.markdown(f"### 📊 شارت القاما الصافية (Net GEX) - الانهاء: [{target_expiration}]")
        if not gex_near.empty:
            fig_gex = go.Figure()
            colors = ['#2ea043' if val >= 0 else '#da3633' for val in gex_near['Net_GEX']]
            
            fig_gex.add_trace(go.Bar(
                x=gex_near['Net_GEX'],
                y=gex_near['strike'].astype(str),
                orientation='h',
                marker_color=colors
            ))

            fig_gex.add_vline(x=0, line_dash="solid", line_color="#8b949e", line_width=1)
            fig_gex.add_hline(y=str(gamma_flip), line_dash="dash", line_color="#a371f7", annotation_text=f"Gamma Flip: ${gamma_flip:.2f}")
            fig_gex.add_hline(y=str(price), line_dash="solid", line_color="#388bfd", annotation_text=f"السعر الحالي: ${price:.2f}")

            fig_gex.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f0f6fc'),
                margin=dict(l=20, r=20, t=30, b=20),
                height=420,
                xaxis=dict(title="صافي القاما Net GEX ($)", gridcolor='#30363d'),
                yaxis=dict(title="سعر الإضراب (Strike)", gridcolor='#30363d', type='category')
            )
            st.plotly_chart(fig_gex, use_container_width=True)
        else:
            st.warning("لا توجد بيانات كافية لعرض شارت القاما ضمن النطاق الحالي.")

        # 4. عمق السيولة والفوليوم بروفايل (Volume Profile)
        st.markdown(f"### 🌊 عمق السيولة والفوليوم بروفايل المباشر ({ticker_symbol})")
        if not c_df.empty and not p_df.empty:
            vol_merged = pd.merge(
                c_df.groupby('strike')['volume'].sum().reset_index().rename(columns={'volume': 'Call_Vol'}),
                p_df.groupby('strike')['volume'].sum().reset_index().rename(columns={'volume': 'Put_Vol'}),
                on='strike', how='outer'
            ).fillna(0)
            
            vol_near = vol_merged[(vol_merged['strike'] >= price * 0.85) & (vol_merged['strike'] <= price * 1.15)]

            if not vol_near.empty:
                fig_vol = go.Figure()
                fig_vol.add_trace(go.Bar(x=vol_near['strike'].astype(str), y=vol_near['Call_Vol'], name='سيولة الكول (Call Vol)', marker_color='#2ea043'))
                fig_vol.add_trace(go.Bar(x=vol_near['strike'].astype(str), y=vol_near['Put_Vol'], name='سيولة البوت (Put Vol)', marker_color='#da3633'))

                fig_vol.update_layout(
                    barmode='stack',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f0f6fc'),
                    margin=dict(l=20, r=20, t=30, b=20),
                    height=380,
                    xaxis=dict(title="سعر الإضراب (Strike)", gridcolor='#30363d'),
                    yaxis=dict(title="حجم العقود (Volume)", gridcolor='#30363d'),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_vol, use_container_width=True)

    except Exception as e:
        st.error(f"حدث خطأ أثناء جلب وتحليل البيانات: {e}")
