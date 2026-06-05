import pandas as pd
from streamlit_echarts import st_echarts
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
import calendar

##################################################################
# CSS
##################################################################

st.markdown("""
<style>

.st-key-heatmap_card {
    background-color: #ffffff !important;
    border-radius: 18px !important;
    padding: 1.2rem !important;
    border: 1px solid rgba(15, 23, 42, 0.05) !important;
    box-shadow:
        0 1px 3px rgba(0, 0, 0, 0.08),
        0 4px 12px rgba(0, 0, 0, 0.08);
}

.st-key-bar_chart_card {
    background-color: white !important;
    border-radius: 18px !important;
    padding: 1.2rem !important;
    border: 1px solid rgba(15,23,42,0.05) !important;
    box-shadow:
        0 1px 3px rgba(0, 0, 0, 0.08),
        0 4px 12px rgba(0, 0, 0, 0.08);
    min-height: 660px !important;
}

</style>
""", unsafe_allow_html=True)


##################################################################
# DATA
##################################################################

@st.cache_data
def load_data():
    df = pd.read_csv("Data/healthcare_clean.csv")
    return df


@st.cache_data
def transform_data(df):
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    for col in ["nps", "csi", "loyalty", "ces"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = df["datetime"].dt.date
    df["year_month"] = df["datetime"].dt.to_period("M")
    return df


TOUCHPOINT_COLUMNS = {
    "registration":       "Registration",
    "doctor_consultation":"Doctor Consultation",
    "nurse_service":      "Nurse Service",
    "pharmacy_service":   "Pharmacy Service",
    "laboratory":         "Laboratory",
    "emergency_response": "Emergency Response",
    "billing_process":    "Billing Process",
    "facility_cleanliness":"Facility Cleanliness",
    "staff_friendliness": "Staff Friendliness",
    "waiting_time":       "Waiting Time",
}


##################################################################
# HELPERS
##################################################################

def apply_branch_filter(df, selected_branches):
    if selected_branches:
        return df[df["branch"].isin(selected_branches)]
    return df.copy()


def get_kpi_avg(df, metric):
    if df is None or df.empty:
        return 0
    return df[metric].mean()


def build_touchpoint_heatmap_data(df):
    month_labels = list(calendar.month_abbr[1:13])
    touchpoint_labels = list(TOUCHPOINT_COLUMNS.values())
    heatmap_data = []
    for y_idx, (col_name, display_name) in enumerate(TOUCHPOINT_COLUMNS.items()):
        monthly_avg = (
            df.groupby(df["datetime"].dt.month)[col_name]
            .mean()
            .reindex(range(1, 13))
        )
        for month_num, value in monthly_avg.items():
            if pd.notna(value):
                heatmap_data.append([
                    month_num - 1,
                    y_idx,
                    round(float(value), 1)
                ])
    return heatmap_data, month_labels, touchpoint_labels


def build_improvement_bar_data(df):
    touchpoint_scores = []
    for col_name, display_name in TOUCHPOINT_COLUMNS.items():
        avg_score = df[col_name].mean()
        if pd.notna(avg_score):
            touchpoint_scores.append({
                "touchpoint": display_name,
                "score": round(float(avg_score), 1)
            })
    bar_df = pd.DataFrame(touchpoint_scores)
    return bar_df.sort_values(by="score", ascending=True).head(3)

def build_touchpoint_quadrant(df):
    quadrant_data = []

    for col_name, display_name in TOUCHPOINT_COLUMNS.items():

        performance = df[col_name].mean()

        impact = (
            df[[col_name, "loyalty"]]
            .corr()
            .iloc[0, 1]
        )

        quadrant_data.append({
            "Touchpoint": display_name,
            "Performance": performance,
            "Impact": impact
        })

    return pd.DataFrame(quadrant_data)


##################################################################
# MAIN
##################################################################

raw_df = load_data()
df = transform_data(raw_df)

# Hilangkan nama rumah sakit dari nama cabang
df["branch"] = df["branch"].str.replace(
    "Always Healthy Hospital ",
    "",
    regex=False
)

##################################################################
# SIDEBAR
##################################################################

with st.sidebar:
    all_branches = sorted(df["branch"].unique())
    selected_branches = st.multiselect("Branch", all_branches, default=all_branches)
    df_branch = apply_branch_filter(df, selected_branches)

    month_options = [
        "January 2025", "February 2025", "March 2025", "April 2025",
        "May 2025", "June 2025", "July 2025", "August 2025",
        "September 2025", "October 2025", "November 2025", "December 2025",
        "Custom"
    ]
    selected_period = st.selectbox("Periode", month_options, index=11)

    if selected_period == "Custom":
        custom_range = st.date_input(
            "Custom Date Range",
            value=(df_branch["datetime"].min().date(), df_branch["datetime"].max().date())
        )


##################################################################
# DATE RANGE LOGIC
##################################################################

if selected_period != "Custom":
    month_map = {
        "January 2025": "2025-01", "February 2025": "2025-02",
        "March 2025": "2025-03", "April 2025": "2025-04",
        "May 2025": "2025-05", "June 2025": "2025-06",
        "July 2025": "2025-07", "August 2025": "2025-08",
        "September 2025": "2025-09", "October 2025": "2025-10",
        "November 2025": "2025-11", "December 2025": "2025-12",
    }
    selected_month = pd.Period(month_map[selected_period], freq="M")
    current_df = df_branch[df_branch["year_month"] == selected_month].copy()
    months = sorted(df_branch["year_month"].unique())
    idx = months.index(selected_month)
    prev_df = None if idx == 0 else df_branch[df_branch["year_month"] == months[idx - 1]].copy()
else:
    if len(custom_range) == 2:
        start_date = pd.to_datetime(custom_range[0])
        end_date = pd.to_datetime(custom_range[1])
    else:
        start_date = df_branch["datetime"].min()
        end_date = df_branch["datetime"].max()
    current_df = df_branch[
        (df_branch["datetime"] >= start_date) &
        (df_branch["datetime"] <= end_date)
    ].copy()


##################################################################
# PAGE
##################################################################

st.title("🔬 Touchpoint Performance")
st.caption("Analysis of touchpoint performance across hospital services.")


##################################################################
# HEATMAP + BAR CHART
##################################################################

left_col, right_col = st.columns([2.99, 0.98])

with left_col:
    with st.container(key="heatmap_card"):

        st.markdown("### Touchpoint Performance Heatmap")
        st.caption(
            "Average touchpoint score by month across all years "
            "(filtered by selected branches only)."
        )

        heatmap_data, month_labels, touchpoint_labels = build_touchpoint_heatmap_data(df_branch)

        max_val = max([row[2] for row in heatmap_data]) if heatmap_data else 5

        heatmap_opts = {
            "tooltip": {
                "position": "top",
                "formatter": """
                function (params) {
                    return 'Touchpoint: ' + params.name +
                        '<br/>Month: ' + params.value[0] +
                        '<br/>Value: ' + params.value[2];
                }
                """,
            },
            "grid": {
                "height": "72%", "top": "8%",
                "bottom": "12%", "left": "1%", "right": "4%",
            },
            "xAxis": {
                "type": "category",
                "data": month_labels,
                "axisLabel": {"rotate": 0, "interval": 0, "fontSize": 11},
            },
            "yAxis": {
                "type": "category",
                "data": touchpoint_labels,
                "axisLabel": {"fontSize": 11, "align": "left", "margin": 120},
            },
            "visualMap": {
                "type": "piecewise",
                "orient": "horizontal",
                "left": "center",
                "bottom": "0%",
                "pieces": [
                    {"min": 1,    "max": 1.5,  "color": "#b91c1c"},
                    {"min": 1.51, "max": 2.0,  "color": "#dc2626"},
                    {"min": 2.01, "max": 2.5,  "color": "#ef4444"},
                    {"min": 2.51, "max": 2.99, "color": "#fca5a5"},
                    {"min": 3.0,  "max": 3.0,  "color": "#d1d5db"},
                    {"min": 3.01, "max": 3.5,  "color": "#bbf7d0"},
                    {"min": 3.51, "max": 4.0,  "color": "#86efac"},
                    {"min": 4.01, "max": 4.5,  "color": "#22c55e"},
                    {"min": 4.51, "max": 5.0,  "color": "#15803d"},
                ]
            },
            "series": [{
                "name": "Touchpoint Score",
                "type": "heatmap",
                "data": heatmap_data,
                "label": {"show": True, "fontSize": 10, "color": "#111827"},
                "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.25)"}},
            }],
        }

        st_echarts(options=heatmap_opts, height="520px", key="touchpoint_heatmap", theme="light")

with right_col:
    with st.container(key="bar_chart_card"):

        st.markdown(
            "<div style='text-align:center; margin-bottom:32px;'>"
                "<div style='font-size:18px; font-weight:700; color:#111827;'>"
                    "Area of Improvement"
                "</div>"
                "<div style='font-size:12px; color:#6b7280; margin-top:4px;'>"
                    "Lowest touchpoint scores"
                "</div>"
            "</div>",
            unsafe_allow_html=True
        )

        bar_df = build_improvement_bar_data(current_df)

        improvement_items = []
        reds = ["#b91c1c", "#ef4444", "#fca5a5"]

        for idx, (_, row) in enumerate(bar_df.iterrows()):
            score_pct      = (row["score"] / 5) * 100
            touchpoint_name = str(row["touchpoint"])
            score_val      = str(row["score"])
            bar_color      = reds[idx]
            bar_width      = f"{score_pct:.1f}%"

            item_html = (
                "<div style='margin-bottom:32px;'>"
                    "<div style='font-size:14px; font-weight:600; color:#374151; margin-bottom:10px;'>"
                        + touchpoint_name +
                    "</div>"
                    "<div style='display:flex; align-items:center; gap:10px;'>"
                        "<div style='flex:1; background:#f3f4f6; border-radius:999px; height:14px; overflow:hidden;'>"
                            "<div style='width:" + bar_width + "; height:100%; background:" + bar_color + "; border-radius:999px;'></div>"
                        "</div>"
                        "<div style='font-size:12px; font-weight:600; color:#111827; min-width:28px;'>"
                            + score_val +
                        "</div>"
                    "</div>"
                "</div>"
            )
            improvement_items.append(item_html)

        st.markdown("".join(improvement_items), unsafe_allow_html=True)

st.markdown("---")

st.subheader("Touchpoint Quadrant Analysis")
st.caption(
    "Touchpoints are classified based on performance and impact on loyalty."
)

quadrant_df = build_touchpoint_quadrant(current_df)

x_mid = quadrant_df["Performance"].mean()
y_mid = quadrant_df["Impact"].mean()

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=quadrant_df["Performance"],
        y=quadrant_df["Impact"],
        mode="markers+text",
        text=quadrant_df["Touchpoint"],
        textposition="top center",
        marker=dict(
    size=22,
    color=quadrant_df["Performance"],
    colorscale="RdYlGn",
    showscale=True,
    line=dict(
        color="white",
        width=2
    ),
    colorbar=dict(
        title="Performance"
    )
)
    )
)

fig.add_vline(
    x=x_mid,
    line_dash="dash",
    line_color="gray"
)

fig.add_hline(
    y=y_mid,
    line_dash="dash",
    line_color="gray"
)

fig.add_annotation(
    x=x_mid - 0.6,
    y=y_mid + 0.25,
    text="<b>Improve Immediately</b>",
    showarrow=False
)

fig.add_annotation(
    x=x_mid + 0.6,
    y=y_mid + 0.25,
    text="<b>Maintain Strengths</b>",
    showarrow=False
)

fig.add_annotation(
    x=x_mid - 0.6,
    y=y_mid - 0.25,
    text="<b>Low Priority</b>",
    showarrow=False
)

fig.add_annotation(
    x=x_mid + 0.6,
    y=y_mid - 0.25,
    text="<b>Nice to Have</b>",
    showarrow=False
)

fig.update_layout(
    height=650,

    plot_bgcolor="#f8fafc",
    paper_bgcolor="#f8fafc",

    xaxis_title="Performance",
    yaxis_title="Impact on Loyalty",

    margin=dict(l=40, r=40, t=40, b=40),

    font=dict(
        color="#111827",
        size=12
    )
)

fig.update_xaxes(
    showgrid=True,
    gridcolor="rgba(0,0,0,0.08)"
)

fig.update_yaxes(
    showgrid=True,
    gridcolor="rgba(0,0,0,0.08)"
)

st.plotly_chart(fig, use_container_width=True)