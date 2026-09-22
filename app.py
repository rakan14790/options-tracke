import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="جدول عقود الخيارات - الدفتر", layout="wide")

st.title("📊 جدول عقود الخيارات (Call & Put)")

# القائمة الجانبية للإعدادات
st.sidebar.header("⚙️ إعدادات البحث والفلترة")
ticker_symbol = st.sidebar.text_input("رمز السهم", value="NVDA").upper()
num_strikes = st.sidebar.select_slider("عدد السترايكات (حول السعر الحالي)", options=[20, 30, 50, "ALL"], value=30)

# اختيار نوع التصفية للتاريخ
view_type = st.sidebar.radio("نوع التصفية للتاريخ", ["الكل", "أسبوعي / يومي (الاثنين، الأربعاء، الجمعة)", "شهري (الجمعة الثالثة)"])

if ticker_symbol:
    try:
        stock = yf.Ticker(ticker_symbol)
        price = stock.fast_info['lastPrice']
        
        col_price, col_time = st.columns([1, 2])
        with col_price:
            st.metric(label=f"سعر {ticker_symbol} الحالي", value=f"${price:.2f}")
        with col_time:
            st.caption("ℹ️ تنبيه: يتم تحديث الـ Open Interest مرة واحدة يومياً قبل الافتتاح بناءً على تسوية اليوم السابق.")

        expirations = stock.options
        if expirations:
            # أيام الأسبوع بالعربي
            days_ar = {
                "Monday": "الاثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء", 
                "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد"
            }
            
            exp_options = []
            for exp in expirations:
                dt = datetime.strptime(exp, "%Y-%m-%d")
                day_name = days_ar.get(dt.strftime("%A"), dt.strftime("%A"))
                
                # تصنيف العقود الشهرية (الجمعة الثالثة من الشهر)
                is_monthly = (dt.weekday() == 4 and 15 <= dt.day <= 21)
                
                # تطبيق الفلتر
                if view_type == "شهري (الجمعة الثالثة)" and not is_monthly:
                    continue
                elif view_type == "أسبوعي / يومي (الاثنين، الأربعاء، الجمعة)" and dt.weekday() not in [0, 2, 4]:
                    continue
                
                label = f"{exp} ({day_name})" + (" - شهري" if is_monthly else "")
                exp_options.append((label, exp))

            if exp_options:
                selected_tuple = st.selectbox(
                    "اختر تاريخ الانتهاء", 
                    options=exp_options, 
                    format_func=lambda x: x[0]
                )
                selected_exp = selected_tuple[1]

                opt = stock.option_chain(selected_exp)
                
                calls = opt.calls[['strike', 'lastPrice', 'bid', 'ask', 'openInterest', 'volume']].copy()
                puts = opt.puts[['strike', 'lastPrice', 'bid', 'ask', 'openInterest', 'volume']].copy()

                # دمج الكول والبوت حسب السترايك
                df = pd.merge(calls, puts, on='strike', suffixes=('_Call', '_Put'), how='outer').sort_values('strike').fillna(0)

                # فلترة عدد السترايكات القريبة من سعر السهم
                if num_strikes != "ALL":
                    df['price_diff'] = (df['strike'] - price).abs()
                    df = df.nsmallest(num_strikes, 'price_diff').sort_values('strike')
                    df = df.drop(columns=['price_diff'])

                # ترتيب الأعمدة على شكل دفتر (الكول يسار، السترايك وسط، البوت يمين)
                df_display = pd.DataFrame({
                    'OI (Call)': df['openInterest_Call'].astype(int),
                    'Vol (Call)': df['volume_Call'].astype(int),
                    'سعر (Call)': df['lastPrice_Call'],
                    'STRIKE': df['strike'],
                    'سعر (Put)': df['lastPrice_Put'],
                    'Vol (Put)': df['volume_Put'].astype(int),
                    'OI (Put)': df['openInterest_Put'].astype(int)
                })

                # عرض الجدول بشكل احترافي
                st.dataframe(
                    df_display.style.highlight_max(subset=['OI (Call)', 'OI (Put)'], color='#1f3a2b'), 
                    use_container_width=True, 
                    height=650
                )
            else:
                st.warning("لا توجد عقود مطابقة لنوع الفلتر المحدد.")
        else:
            st.warning("لا توجد بيانات خيارات متاحة لهذا السهم.")

    except Exception as e:
        st.error(f"حدث خطأ أثناء جلب البيانات: {e}")
