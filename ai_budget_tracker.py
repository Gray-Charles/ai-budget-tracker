import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe

# --- Page Setup ---
st.set_page_config(page_title="💸 AI Budget Tracker", layout="wide")
st.title("💸 AI Budget Tracker")

st.markdown("""
Welcome to your personal budget dashboard.  
Upload a file or try the sample to get instant visual insights and predictions.
""")

# --- File Upload Option (CSV or Excel) ---
uploaded_file = st.file_uploader("📤 Optional: Upload your budget file (CSV or Excel)", type=["csv", "xlsx"])
if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    st.session_state.df = df
    st.success("✅ File uploaded successfully!")

# --- Google Sheets Option ---
with st.expander("📋 Connect Google Sheet (Optional)"):
    st.markdown("""
**Step 1:** [📄 Make a copy of the sample sheet](https://docs.google.com/spreadsheets/d/1YRbXQpV0VCvsfDs8IDNpx2ycx92pN-H4Dy20QY9p1CI/copy)  
**Step 2:** Share with: `budget-bot@yourproject.iam.gserviceaccount.com`  
**Step 3:** Paste your Google Sheet URL below:
""")
    user_sheet_url = st.text_input("Paste Google Sheet URL:")

    try:
        gc = gspread.service_account(filename="C:/Users/crg74/Desktop/AI_Budget_Tracker_Project/Keys/creds.json")
        if user_sheet_url:
            sheet = gc.open_by_url(user_sheet_url)
            worksheet = sheet.sheet1
            df = get_as_dataframe(worksheet).dropna(how="all")
            st.session_state.df = df
            st.success("✅ Google Sheet loaded successfully!")
        elif not uploaded_file:
            st.warning("👆 Upload a file above or paste Google Sheet URL to begin.")
    except Exception as e:
        st.error("❌ Could not connect to Google Sheets.")
        st.exception(e)

# --- Sample Data Button ---
if st.button("🧪 Try Sample Budget"):
    df = pd.DataFrame({
        "Date": pd.date_range(start="2024-01-01", periods=6, freq="M"),
        "Income Amount": [3000, 3200, 3100, 3050, 3150, 3300],
        "Expense Amount": [2000, 2100, 1900, 2200, 2050, 2150],
        "Expense Category": ["Groceries", "Utilities", "Transportation", "Groceries", "Utilities", "Transportation"]
    })
    st.session_state.df = df
    st.success("✅ Sample data loaded!")

df = st.session_state.get("df", pd.DataFrame())

# --- Column Detection ---
def find_column(possible, df):
    for name in possible:
        if name in df.columns:
            return name
    return None

income_col = find_column(["Income Amount", "Income", "Earnings"], df)
expense_col = find_column(["Expense Amount", "Expenses", "Spending"], df)
date_col = find_column(["Date", "Transaction Date"], df)
category_col = find_column(["Expense Category", "Category", "Spending Category"], df)

# --- Budget Metrics ---
if not df.empty and income_col and expense_col:
    total_income = df[income_col].sum()
    total_expenses = df[expense_col].sum()
    balance = total_income - total_expenses
    spend_ratio = (total_expenses / total_income) * 100 if total_income else 0
else:
    total_income = total_expenses = balance = spend_ratio = 0

st.markdown("### 📊 Financial Overview")
a, b, c = st.columns(3)
a.metric("💰 Income", f"${total_income:,.2f}")
b.metric("💸 Expenses", f"${total_expenses:,.2f}")
c.metric("📈 Balance", f"${balance:,.2f}")

if spend_ratio > 85:
    st.warning(f"⚠️ You're spending {spend_ratio:.1f}% of your income. Consider budgeting tweaks.")

# --- Top Spending Category Insight ---
if not df.empty and category_col and expense_col:
    top_cat = df.groupby(category_col)[expense_col].sum().idxmax()
    top_amt = df.groupby(category_col)[expense_col].sum().max()
    st.info(f"Your top spending category this cycle is **{top_cat}** at ${top_amt:,.2f}.")

# --- Charts ---
if not df.empty and date_col and expense_col and category_col:
    try:
        chart_df = df.dropna(subset=[date_col, expense_col, category_col]).copy()
        chart_df[date_col] = pd.to_datetime(chart_df[date_col], errors="coerce")
        chart_df = chart_df.dropna(subset=[date_col])
        chart_df["Month"] = chart_df[date_col].dt.to_period("M").astype(str)

        st.markdown("### 🗓️ Monthly Expense Trend")
        monthly_exp = chart_df.groupby("Month")[expense_col].sum().reset_index()
        st.line_chart(monthly_exp, x="Month", y=expense_col)

        st.markdown("### 🍽️ Category Breakdown")
        cat_totals = chart_df.groupby(category_col)[expense_col].sum().sort_values()
        st.bar_chart(cat_totals)

        st.markdown("### 🔄 Month-over-Month Spending Summary")
        main_col, detail_col = st.columns([1, 1])

        # 📈 Left Column – Interactive Chart + Table Toggle
        with main_col:
            monthly_exp = chart_df.groupby("Month")[expense_col].sum().reset_index()
            monthly_exp["Change"] = monthly_exp[expense_col].diff()

            # Optional: Switch to Altair for hover tooltips
            import altair as alt
            line_chart = alt.Chart(monthly_exp).mark_line(point=True).encode(
                x="Month",
                y=expense_col,
                tooltip=["Month", expense_col, "Change"]
            ).properties(height=300)

            st.altair_chart(line_chart, use_container_width=True)
            st.caption("Monthly spending trend. Hover points for values.")

            with st.expander("📊 View Monthly Values Table"):
                st.dataframe(monthly_exp)

        # 🕵️ Right Column – Driver Breakdown
        with detail_col:
            st.markdown("#### 🕵️ Category Drivers Each Month")

            monthly_categories = chart_df.groupby(["Month", category_col])[expense_col].sum().unstack(fill_value=0)
            category_deltas = monthly_categories.diff().dropna()

            for month in category_deltas.index:
                changes = category_deltas.loc[month]
                significant_changes = changes[changes != 0].sort_values(key=abs, ascending=False).head(3)

                if not significant_changes.empty:
                     net_change = changes.sum()
                     direction = "increase" if net_change > 0 else "decrease"
                     emoji = "🔺" if net_change > 0 else "🔻"

                     with st.expander(f"{emoji} {month} — Spending {direction} of ${net_change:+,.2f}"):
                        driver_table = pd.DataFrame({
                            "Category": significant_changes.index,
                            "Change Amount": significant_changes.apply(lambda x: f"${x:+,.2f}")
                        })
                        st.table(driver_table)

    except Exception as e:
        st.warning(f"Chart error: {e}")

# --- Forecast Section ---
with st.expander("🔮 Market Outlook & Spending Impact", expanded=True):
    forecast_aliases = {
        "Groceries 🛒": ["groceries", "food", "supermarket", "grocery"],
        "Transportation 🚗": ["transportation", "gas", "fuel", "car", "commute"],
        "Utilities ⚡": ["utilities", "electric", "water", "power", "gas bill", "energy"]
    }
    forecast_factors = {
        "Groceries 🛒": 0.015,
        "Transportation 🚗": -0.008,
        "Utilities ⚡": 0.022
    }
    matched = set()
    forecast_table = []

    if category_col and expense_col:
        spend_by_cat = df.groupby(category_col)[expense_col].sum()

        for label, aliases in forecast_aliases.items():
            match = None
            for c in spend_by_cat.index:
                if c in matched:
                    continue
                if any(a in c.lower() for a in aliases):
                    match = c
                    break
            if match:
                matched.add(match)
                current = spend_by_cat[match]
                pct = forecast_factors[label]
                projected = current * (1 + pct)
                delta = projected - current

                forecast_table.append({
                    "Category": label,
                    "You Spent": f"${current:,.2f}",
                    "Forecast": f"{pct:+.1%}",
                    "Est. Next Month": f"${projected:,.2f}",
                    "Change": f"${delta:+.2f}"
                })

    if forecast_table:
        st.markdown("#### 📈 Predicted Changes Based on Market Trends")
        forecast_df = pd.DataFrame(forecast_table)
        st.table(forecast_df)

        if st.download_button("📥 Download Forecast Summary", forecast_df.to_csv(index=False), "market_forecast.csv"):
            st.success("Forecast saved!")

        hot = max(forecast_table, key=lambda x: abs(float(x["Change"].replace("$", "").replace(",", ""))))
        trend = "increase" if "-" not in hot["Change"] else "decrease"
        st.info(f"Your **{hot['Category']}** costs may {trend} by {hot['Forecast']} next month.")

# --- Raw Data Viewer (Always Visible) ---
with st.expander("🔍 View Uploaded Budget Data", expanded=True):
    if "df" in st.session_state and not st.session_state.df.empty:
        st.dataframe(st.session_state.df)
    else:
        st.write("No data loaded yet. Upload a file, paste a Google Sheet, or load the sample above.")