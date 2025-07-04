import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
# import firebase_admin
# from firebase_admin import credentials, firestore

# # ---- Firebase Initialization ----
# if not firebase_admin._apps:
#     cred = credentials.Certificate("serviceAccountKey.json")  # Make sure this file exists
#     firebase_admin.initialize_app(cred)
# db = firestore.client()

# def upload_to_firestore(dataframe):
#     for _, row in dataframe.iterrows():
#         doc_ref = db.collection('inventory').document(row['Product_Name'])
#         doc_ref.set(row.to_dict())

# ---- Streamlit Page Config ----
st.set_page_config(page_title="EcoShelf AI", layout="wide", page_icon="🛒")

# ---- Sidebar ----
st.sidebar.image("assets/logo2.jpg", width=120)
st.sidebar.markdown("## 🎨 Choose Theme")
theme = st.sidebar.radio("Theme", ["Light", "Dark"])
st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("📁 Upload your perishable inventory CSV file", type="csv")

# ---- Header ----
st.markdown(
    "<h1 style='text-align: center; color: #4CAF50;'>🛒 EcoShelf AI</h1>"
    "<h4 style='text-align: center; color: grey;'>Smart Spoilage & Stock Predictor for Retailers</h4>",
    unsafe_allow_html=True
)

# ---- Main Logic ----
if uploaded_file is None:
    st.info("📂 Upload your CSV file to get started.")
else:
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip()

        required_columns = ['Product_Name', 'Arrival_Date', 'Expiry_Date', 'Quantity', 'Daily_Sales']
        if all(col in df.columns for col in required_columns):

            # Convert date columns
            df['Arrival_Date'] = pd.to_datetime(df['Arrival_Date'])
            df['Expiry_Date'] = pd.to_datetime(df['Expiry_Date'])

            # Calculate Days Left
            today = datetime.now()
            df['Days_Left'] = (df['Expiry_Date'] - today).dt.days

            # Spoilage Risk Calculation
            def get_spoilage_risk(days):
                if days <= 0:
                    return "Expired"
                elif days <= 2:
                    return "High"
                elif days <= 5:
                    return "Medium"
                else:
                    return "Low"

            df['Spoilage_Risk'] = df['Days_Left'].apply(get_spoilage_risk)
            df['Stock_Out_Days'] = (df['Quantity'] / df['Daily_Sales']).apply(lambda x: int(x) if x >= 0 else 0)
            df['Stock_Out_Date'] = df['Arrival_Date'] + pd.to_timedelta(df['Stock_Out_Days'], unit='D')

            # Upload to Firebase
            # upload_to_firestore(df)

            # ---- Inventory Table ----
            st.markdown("### 📦 Inventory Overview")
            styled_df = df.style.applymap(
                lambda val: 'color: white; background-color: crimson;' if val == "Expired"
                else 'color: black; background-color: orange;' if val == "High"
                else 'color: black; background-color: gold;' if val == "Medium"
                else 'color: white; background-color: green;',
                subset=['Spoilage_Risk']
            )
            st.dataframe(styled_df, use_container_width=True)

            # ---- Graphs ----
            st.markdown("### 📊 Risk & Stock Insights")
            col1, col2 = st.columns(2)

            with col1:
                risk_counts = df['Spoilage_Risk'].value_counts().reset_index()
                risk_counts.columns = ['Spoilage_Risk', 'count']
                pie_fig = px.pie(risk_counts, names='Spoilage_Risk', values='count',
                                 title="Spoilage Risk Levels",
                                 color='Spoilage_Risk',
                                 color_discrete_map={'Low': 'lightgreen', 'Medium': 'gold',
                                                     'High': 'orange', 'Expired': 'crimson'})
                st.plotly_chart(pie_fig, use_container_width=True)

            with col2:
                bar_fig = px.bar(df.sort_values('Stock_Out_Date'),
                                 x='Product_Name', y='Stock_Out_Days', color='Spoilage_Risk',
                                 title="⏳ Days Until Stock-Out",
                                 labels={'Stock_Out_Days': 'Days Left'})
                st.plotly_chart(bar_fig, use_container_width=True)

            # ---- Metrics ----
            st.markdown("### 📌 Summary")
            col3, col4, col5 = st.columns(3)
            col3.metric("Total Products", df.shape[0])
            col4.metric("Expired", (df['Spoilage_Risk'] == "Expired").sum())
            col5.metric("High Risk", (df['Spoilage_Risk'] == "High").sum())

            # ---- Notifications ----
            st.markdown("### 🔔 Notifications")
            expiring_soon = df[df['Days_Left'] <= 2]
            if not expiring_soon.empty:
                st.warning(f"⚠️ {len(expiring_soon)} products are expiring soon!")

            stock_out_soon = df[df['Stock_Out_Days'] <= 2]
            if not stock_out_soon.empty:
                st.warning(f"🚨 {len(stock_out_soon)} products will go out of stock soon!")

            # ---- Countdown Timers ----
            st.markdown("### ⏳ Countdown Timers")
            countdown_df = df[['Product_Name', 'Expiry_Date', 'Stock_Out_Date']].copy()
            countdown_df = countdown_df.sort_values(by='Expiry_Date')

            for _, row in countdown_df.iterrows():
                expiry_delta = row['Expiry_Date'] - datetime.now()
                stockout_delta = row['Stock_Out_Date'] - datetime.now()

                colA, colB, colC = st.columns([2, 2, 6])
                with colA:
                    st.markdown(f"**🛒 {row['Product_Name']}**")
                with colB:
                    st.success(f"📆 Expiry in: {expiry_delta.days} days" if expiry_delta.days >= 0 else "❌ Expired")
                with colC:
                    st.info(f"📦 Stock ends in: {stockout_delta.days} days" if stockout_delta.days >= 0 else "⚠️ Out of Stock")

            # ---- CSV Download ----
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download Cleaned CSV", csv, file_name="EcoShelf_Inventory_Updated.csv", mime='text/csv')

            # ---- EcoBot ----
            st.markdown("### 🤖 Ask EcoBot")
            question = st.text_input("Type your question about inventory or spoilage:")
            if question:
                if "expire" in question.lower():
                    st.info("EcoBot: Products with 0 or fewer days left are considered expired.")
                elif "stock" in question.lower():
                    st.info("EcoBot: Stock-out = Quantity ÷ Daily Sales.")
                elif "risk" in question.lower():
                    st.info("EcoBot: Risk levels depend on days left before expiry.")
                else:
                    st.info("EcoBot: Try asking about expiry, stock-out, or risk.")

        else:
            st.error("❌ CSV must contain columns: Product_Name, Arrival_Date, Expiry_Date, Quantity, Daily_Sales")

    except Exception as e:
        st.error(f"❌ Error: {e}")
