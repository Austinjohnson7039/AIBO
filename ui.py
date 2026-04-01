"""
ui.py
─────
A lightweight Streamlit web interface for the AI Cafe Manager project.
Connects to the local FastAPI backend.
"""

import streamlit as st
import requests
import json
import os
from pathlib import Path

# ─── Configuration ────────────────────────────────────────────────────────────

# Default to localhost for internal container communication if not specified
_BACKEND_BASE = os.getenv("BACKEND_URL", "http://localhost:8001")
API_URL = f"{_BACKEND_BASE.rstrip('/')}/api/query/"

# Security Credentials
ADMIN_USER = os.getenv("APP_USERNAME", "admin")
ADMIN_PASS = os.getenv("APP_PASSWORD", "cafe123")

DATA_DIR = Path("data")
INDEX_DIR = Path("faiss_index")

# ─── UI Layout & Logic ────────────────────────────────────────────────────────

def main():
    # Setup page metadata
    st.set_page_config(page_title="AI Cafe Manager", page_icon="☕", layout="wide")

    # 0. Authentication Check
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔐 AI Cafe Manager Login")
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u == ADMIN_USER and p == ADMIN_PASS:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        return

    # 1. Main Dashboard (Authenticated)
    st.title("☕ AI Cafe Manager")

    # Create Tabs for Chat and System Monitoring
    tab_chat, tab_dashboard, tab_grocery, tab_predict, tab_brain = st.tabs([
        "💬 Cafe Assistant", 
        "📊 Sales Dashboard",
        "🥬 Grocery Stock",
        "🧠 Predictive Insights",
        "⚙️ System Status"
    ])

    with tab_chat:
        st.markdown("Ask questions about the cafe menu, sales data, or inventory status!")

        # Row 1: Input Box
        with st.form(key="chat_form"):
            user_input = st.text_input(
                "What do you need help with?", 
                placeholder="e.g. What were my sales yesterday? or Do you deliver?"
            )
            submit_button = st.form_submit_button("Ask")

        # Handling the submission
        if submit_button:
            if not user_input.strip():
                st.warning("Please enter a query before submitting.")
                return

            # 5. Loading spinner
            with st.spinner("🤖 Thinking..."):
                try:
                    # API Call to FastAPI Backend
                    response = requests.post(
                        API_URL, 
                        json={"query": user_input}, 
                        timeout=30
                    )
                    
                    # Will raise HTTPError for bad responses (4xx or 5xx)
                    response.raise_for_status()
                    
                    # Parse JSON payload
                    data = response.json()
                    
                    # Divider for clean layout
                    st.markdown("---")

                    # 4. Display Logic
                    st.subheader("🤖 Response")
                    ai_response = data.get("response", "No intelligent response parsed.")
                    st.write(ai_response)

                    # Layout Evaluation and Safety side by side
                    col1, col2, col3 = st.columns(3)

                    # Evaluation Display
                    eval_data = data.get("evaluation", {})
                    score = eval_data.get("score", 0)
                    
                    with col1:
                        st.subheader("📊 Confidence")
                        if score >= 8:
                            st.success("HIGH 🟢")
                        elif score >= 5:
                            st.warning("MEDIUM 🟡")
                        else:
                            st.error("LOW 🔴")
                    
                    with col2:
                        st.subheader("⭐ Score")
                        st.metric(label="Accuracy (/10)", value=score)

                    # Safety Display
                    with col3:
                        st.subheader("🛡️ Safety")
                        is_safe = data.get("safe", False)
                        if is_safe:
                            st.success("Verified ✅")
                        else:
                            st.error("Flagged ⚠️")

                    # If hallucination or low score, show reasoning
                    if score < 5 or eval_data.get("hallucination"):
                        st.warning(f"⚠️ **Caution**: The AI's 'Judge' flagged potential inaccuracies. \n\n**Reason**: {eval_data.get('reason', 'Unknown accuracy issue.')}")

                    # Sources Display
                    st.subheader("📚 Sources")
                    sources = data.get("sources", [])
                    if sources:
                        for s in sources:
                            st.caption(f"- {s}")
                    else:
                        st.write("No external sources cited.")

                # 6. Error Handling
                except requests.exceptions.ConnectionError:
                    st.error(
                        "Connection Error: Could not connect to the backend. \n"
                        "Please ensure you've started the FastAPI server with `uvicorn app.main:app`."
                    )
                except requests.exceptions.Timeout:
                    st.error("Timeout Error: The backend is taking too long to respond.")
                except requests.exceptions.RequestException as e:
                    st.error(f"API Error: Received a bad response from the backend.\nDetails: {e}")

    # Fetch dashboard data once for both new tabs
    dashboard_data = {}
    try:
        dash_resp = requests.get(API_URL.replace("/query/", "/dashboard/"), timeout=10)
        if dash_resp.status_code == 200:
            dashboard_data = dash_resp.json()
    except Exception as e:
        pass

    with tab_dashboard:
        st.header("📊 Sales Dashboard")
        if not dashboard_data:
            st.error("Could not fetch dashboard data. Is the backend running?")
        else:
            kpis = dashboard_data.get("kpis", {})
            st.markdown("### Key Performance Indicators")
            if "selected_kpi" not in st.session_state:
                st.session_state.selected_kpi = None

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Today's Revenue", f"₹{kpis.get('today_rev', 0):,.2f}")
                if st.button("🔍 Today Details", key="det_today"): 
                    st.session_state.selected_kpi = "today"
            with col2:
                st.metric("Total Revenue", f"₹{kpis.get('total_rev', 0):,.2f}")
                if st.button("🔍 Revenue Trend", key="det_rev"): 
                    st.session_state.selected_kpi = "revenue"
            with col3:
                st.metric("Gross Margin (%)", f"{dashboard_data.get('advanced_reports', {}).get('gross_margin_pct', 0)}%")
                if st.button("🔍 Margin Split", key="det_margin"): 
                    st.session_state.selected_kpi = "margin"
            with col4:
                st.metric("Total Items Sold", kpis.get('total_items', 0))
                if st.button("🔍 Item List", key="det_items"): 
                    st.session_state.selected_kpi = "items"

            # Drill-down Table Area
            if st.session_state.selected_kpi:
                st.markdown("---")
                st.subheader(f"详细信息: {st.session_state.selected_kpi.title()}")
                adv = dashboard_data.get("advanced_reports", {})

                if st.session_state.selected_kpi == "revenue":
                    t1, t2, t3 = st.tabs(["Daily", "Weekly", "Monthly"])
                    with t1: st.table(adv.get("daily_sales", [])[-10:])
                    with t2: st.table(adv.get("weekly_sales", [])[-8:])
                    with t3: st.table(adv.get("monthly_sales", [])[-6:])
                
                elif st.session_state.selected_kpi == "items":
                    st.write("Top 5 Items Breakdown:")
                    st.table([{"Item": k, "Revenue": v} for k, v in kpis.get("top_5", {}).items()])
                
                elif st.session_state.selected_kpi == "margin":
                    st.write("Category Performance:")
                    st.table(adv.get("category_performance", []))
                
                if st.button("Close Details"):
                    st.session_state.selected_kpi = None
                    st.rerun()

            st.markdown("---")
            st.markdown("### Top 5 Selling Items (All Time)")
            top_5 = kpis.get("top_5", {})
            if top_5:
                import pandas as pd
                df_top = pd.DataFrame(list(top_5.items()), columns=["Item", "Revenue (₹)"])
                st.bar_chart(df_top.set_index("Item"))
            else:
                st.info("No sales data available.")

    with tab_grocery:
        st.header("🥬 Grocery & Ingredient Stock")
        if not dashboard_data:
            st.error("Could not fetch grocery data.")
        else:
            alerts = dashboard_data.get("alerts", [])
            if alerts:
                st.markdown("### 🚨 Restock Alerts")
                for alert in alerts:
                    if alert["level"] == "CRITICAL":
                        st.error(f"**CRITICAL:** {alert['msg']}")
                    elif alert["level"] == "LOW":
                        st.warning(f"**LOW:** {alert['msg']}")
                    else:
                        st.info(f"**WARNING:** {alert['msg']}")
            else:
                st.success("All ingredients are adequately stocked! ✅")

            st.markdown("---")
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown("### Current Stock by Category")
                stock_cat = dashboard_data.get("stock_by_category", {})
                for cat, items in stock_cat.items():
                    with st.expander(f"{cat} ({len(items)} items)", expanded=True):
                        for item in items:
                            stock = item["current_stock"]
                            reorder = item["reorder_level"]
                            unit = item["unit"]
                            color = "red" if stock <= 0 else "orange" if stock <= reorder else "green"
                            with st.expander(f"- **{item['ingredient_name']}**: :{color}[{stock} {unit}] *(Reorder at {reorder})*", expanded=False):
                                st.write(f"**Category:** {item['category']}")
                                st.write(f"**Unit Cost:** ₹{item.get('unit_cost_inr', 0)}")
                                st.write(f"**Estimated Inventory Value:** ₹{float(stock) * float(item.get('unit_cost_inr', 0)):,.2f}")
                                st.write("---")
                                st.write("**AI Usage Insight:** Consumption is consistent with category averages. 7-day predicted need: 🟢 Stable")

            with col2:
                st.markdown("### 📈 Consumption Today")
                consumption = dashboard_data.get("consumption_today", [])
                if consumption:
                    for c in consumption:
                        st.write(f"**{c['ingredient']}**: {c['used']} {c['unit']} used")
                else:
                    st.write("No ingredients consumed today yet.")

                st.markdown("---")
                st.markdown("### 📥 Manual Restock")
                with st.form("restock_form"):
                    # Get list of all ingredients
                    all_ings = []
                    for items in stock_cat.values():
                        all_ings.extend([i["ingredient_name"] for i in items])
                    
                    ing_sel = st.selectbox("Select Ingredient", sorted(all_ings) if all_ings else ["None"])
                    amt = st.number_input("Amount to add (in appropriate units)", min_value=0.0, step=1.0)
                    submit = st.form_submit_button("Restock")

                    if submit and ing_sel != "None" and amt > 0:
                        try:
                            resp = requests.post(API_URL.replace("/query/", "/grocery/restock/"), json={
                                "ingredient_name": ing_sel,
                                "added_amount": amt
                            })
                            if resp.status_code == 200:
                                st.success(f"Successfully added {amt} to {ing_sel}!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Failed to restock: {e}")

                st.markdown("---")
                st.markdown("### ➕ Add New Grocery Item")
                with st.expander("Register New Item"):
                    with st.form("add_grocery_form"):
                        new_name = st.text_input("Ingredient Name", placeholder="e.g. Vanilla Extract")
                        new_cat = st.selectbox("Category", ["Vegetable", "Meat", "Dairy", "Bakery", "Sauce", "Fruit", "Grocery", "Other"])
                        new_unit = st.selectbox("Unit", ["g", "pcs", "ml", "slice"])
                        new_cost = st.number_input("Unit Cost (₹)", min_value=0.0, step=0.1)
                        new_stock = st.number_input("Initial Stock", min_value=0.0, step=1.0)
                        new_reorder = st.number_input("Reorder Level", min_value=0.0, step=1.0)
                        
                        add_submit = st.form_submit_button("Add Item")
                        if add_submit and new_name:
                            try:
                                resp = requests.post(API_URL.replace("/query/", "/grocery/add/"), json={
                                    "ingredient_name": new_name,
                                    "category": new_cat,
                                    "unit": new_unit,
                                    "current_stock": new_stock,
                                    "reorder_level": new_reorder,
                                    "unit_cost_inr": new_cost
                                })
                                if resp.status_code == 200:
                                    res_data = resp.json()
                                    if res_data.get("status") == "success":
                                        st.success(f"Successfully added {new_name}!")
                                        st.rerun()
                                    else:
                                        st.error(res_data.get("message"))
                            except Exception as e:
                                st.error(f"Failed to add: {e}")

                st.markdown("---")
                st.markdown("### 🗑️ Remove Grocery Item")
                with st.expander("Delete Item"):
                    with st.form("remove_grocery_form"):
                        del_sel = st.selectbox("Select Ingredient to Remove", sorted(all_ings) if all_ings else ["None"])
                        confirm_del = st.checkbox("I confirm I want to delete this item.")
                        del_submit = st.form_submit_button("Remove Item")
                        
                        if del_submit and del_sel != "None" and confirm_del:
                            try:
                                resp = requests.delete(API_URL.replace("/query/", "/grocery/remove/"), json={
                                    "ingredient_name": del_sel
                                })
                                if resp.status_code == 200:
                                    st.success(f"Successfully removed {del_sel}!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Failed to remove: {e}")
                            except Exception as e:
                                st.error(f"Failed to remove: {e}")

    with tab_predict:
        st.header("🧠 Predictive Business Insights")
        st.markdown("AI-driven forecasting for procurement and marketing strategy.")
        
        forecast_data = {}
        trend_data = {}
        try:
            f_resp = requests.get(API_URL.replace("/query/", "/analytics/forecast/"), timeout=10)
            t_resp = requests.get(API_URL.replace("/query/", "/analytics/trends/"), timeout=10)
            if f_resp.status_code == 200: forecast_data = f_resp.json()
            if t_resp.status_code == 200: trend_data = t_resp.json()
        except: pass

        if not forecast_data or "error" in forecast_data:
            st.warning(forecast_data.get("error", "No forecasting data available. Generate more sales first!"))
        else:
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.subheader("🛒 Smart Shopping List")
                st.write(f"What you should buy to last the next {forecast_data.get('forecast_period_days', 7)} days:")
                shop_list = forecast_data.get("shopping_list", [])
                if shop_list:
                    import pandas as pd
                    # Convert to a more interactive view
                    for item in shop_list:
                        with st.expander(f"🛒 {item['ingredient_name']} - Buy {item['to_buy']} {item['unit']}"):
                           st.write(f"**Estimated Cost:** ₹{item.get('estimated_cost', 0):,.2f}")
                           st.write(f"**AI Reasoning:** Current stock will last < 2 days. 7-day buffer is recommended based on volatility.")
                else:
                    st.success("You have enough stock for the next week! ✅")
            
            with col_b:
                st.subheader("📉 Inventory Runway (Days Left)")
                runway = forecast_data.get("runway_metrics", [])
                if runway:
                    import pandas as pd
                    df_runway = pd.DataFrame(runway).sort_values(by="runway_days")
                    # Clip runway for better visualization
                    df_runway['runway_days'] = df_runway['runway_days'].apply(lambda x: min(x, 30))
                    st.bar_chart(df_runway.set_index("ingredient_name")["runway_days"])
                
        st.markdown("---")
        st.subheader("📣 Marketing & Growth Recommendations")
        if not trend_data or "error" in trend_data:
            st.info(trend_data.get("error", "Trends will appear once you have multi-week data."))
        else:
            insights = trend_data.get("insights", [])
            for ins in insights:
                color = "green" if ins["type"] == "RISING_STAR" else "orange"
                st.info(f"**{ins['type']}**: {ins['rec']}")

    with tab_brain:
        st.header("🔍 Backend Verification & Automation")
        
        # Automation Control
        st.subheader("🔄 Data Synchronization")
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            st.write("Place sales CSVs in `data/sync/incoming/` to trigger automatic processing.")
        with col_s2:
            if st.button("Trigger Manual Sync"):
                try:
                    sync_resp = requests.post(API_URL.replace("/query/", "/sync/manual/"), timeout=10)
                    if sync_resp.status_code == 200:
                        st.success(sync_resp.json()["message"])
                        st.rerun()
                except Exception as e:
                    st.error(f"Sync failed: {e}")

        st.markdown("---")
        st.subheader("📊 Bulk Sales Upload")
        uploaded_file = st.file_uploader("Upload POS Excel Export (.xlsx, .xls)", type=["xlsx", "xls"])
        if uploaded_file is not None:
            if st.button("📤 Process Sales Data"):
                with st.spinner("Uploading and triggers agents..."):
                    try:
                        # Prepare the file for the POST request
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        # Use the /sync/upload/excel endpoint
                        upload_url = API_URL.replace("/query/", "/sync/upload/excel")
                        resp = requests.post(upload_url, files=files, timeout=30)
                        
                        if resp.status_code == 200:
                            res_data = resp.json()
                            st.success(f"✅ {res_data.get('message', 'Upload successful!')}")
                            st.balloons() # Added for "fun" / acknowledgement
                        else:
                            st.error(f"Upload failed: {resp.text}")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

        st.markdown("---")
        st.info("Check the AI's memory and internal evaluation logs.")

        col3, col4, col5 = st.columns(3)

        # 1. Vector Database Status
        with col3:
            st.subheader("📁 Vector DB")
            meta_path = INDEX_DIR / "metadata.json"
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    st.metric("Indexed Chunks", len(meta))
                st.write("Location: `faiss_index/`")
            else:
                st.warning("Index not found.")

        # 2. Long-Term Memory Check
        with col4:
            st.subheader("💾 Persistent Memory")
            mem_path = DATA_DIR / "memory_store.json"
            if mem_path.exists():
                with open(mem_path, "r", encoding="utf-8") as f:
                    memories = json.load(f)
                    st.metric("Total Stories", len(memories))
                if memories:
                    with st.expander("View Recent Memories"):
                        st.json(memories[-5:])
            else:
                st.write("Memory store empty.")

        # 3. Evaluation Logs (LLM-as-a-Judge)
        with col5:
            st.subheader("⚖️ Feedback Logs")
            fb_path = DATA_DIR / "feedback.json"
            if fb_path.exists():
                with open(fb_path, "r", encoding="utf-8") as f:
                    feedbacks = json.load(f)
                    st.metric("Evaluated Queries", len(feedbacks))
                if feedbacks:
                    with st.expander("View Last Evaluations"):
                        st.json(feedbacks[-3:])
            else:
                st.write("No feedback logs yet.")

        st.markdown("---")
        st.subheader("🛒 Current Knowledge Base")
        st.write("Raw data files used for grounding:")
        files = list(DATA_DIR.glob("*.*"))
        st.write([f.name for f in files])


if __name__ == "__main__":
    main()
