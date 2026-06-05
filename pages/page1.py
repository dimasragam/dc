import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
import calendar

##################################################################
# CSS
##################################################################

st.markdown("""
<style>

.st-key-kpi_nps,
.st-key-kpi_csi,
.st-key-kpi_loyalty,
.st-key-kpi_ces {
    background-color: #ffffff !important;
    border-radius: 18px !important;
    padding: 0.9rem !important;
    border: 1px solid rgba(15, 23, 42, 0.05) !important;
    box-shadow:
        0 1px 3px rgba(0, 0, 0, 0.08),
        0 4px 12px rgba(0, 0, 0, 0.08);
}
.st-key-satisfaction_card {
    background-color: #ffffff !important;
    border-radius: 18px !important;
    padding: 0.9rem !important;
    border: 1px solid rgba(15, 23, 42, 0.05) !important;
    box-shadow:
        0 1px 3px rgba(0, 0, 0, 0.08),
        0 4px 12px rgba(0, 0, 0, 0.08);
}
.st-key-complaint_card {
    background-color: #ffffff !important;
    border-radius: 18px !important;
    padding: 0.9rem !important;
    border: 1px solid rgba(15, 23, 42, 0.05) !important;
    box-shadow:
        0 1px 3px rgba(0, 0, 0, 0.08),
        0 4px 12px rgba(0, 0, 0, 0.08);
    min-height: 100px !important;

}
.st-key-heatmap_corr_card {
    background-color: #ffffff !important;
    border-radius: 18px !important;
    padding: 0.9rem !important;
    border: 1px solid rgba(15, 23, 42, 0.05) !important;
    box-shadow:
        0 1px 3px rgba(0, 0, 0, 0.08),
        0 4px 12px rgba(0, 0, 0, 0.08);

    min-height: 100px !important;

}         
</style>
""", unsafe_allow_html=True)


##################################################################
# UI TUNING
##################################################################

CHART_VERTICAL_OFFSET = 28
LEFT_CONTENT_OFFSET = 22
CHART_HEIGHT = 45


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


##################################################################
# HELPERS
##################################################################

def apply_branch_filter(df, selected_branches):
    if selected_branches:
        return df[df["branch"].isin(selected_branches)]
    return df.copy()


def get_previous_period_df(df, start_date, end_date):
    current_days = (end_date - start_date).days + 1
    prev_end = start_date - pd.Timedelta(days=1)
    prev_start = prev_end - pd.Timedelta(days=current_days - 1)
    prev_df = df[
        (df["datetime"] >= prev_start) &
        (df["datetime"] <= prev_end)
    ].copy()
    return prev_df


def get_kpi_avg(df, metric):
    if df is None or df.empty:
        return 0
    return df[metric].mean()


def get_delta(curr_val, prev_val):
    if prev_val is None or prev_val == 0:
        return "0.0%", "#94a3b8"
    delta_pct = ((curr_val - prev_val) / prev_val) * 100
    if delta_pct > 0:
        return f"▲ {delta_pct:.1f}%", "#16a34a"
    elif delta_pct < 0:
        return f"▼ {abs(delta_pct):.1f}%", "#dc2626"
    else:
        return "0.0%", "#94a3b8"


def get_badge_bg(delta_color):
    if delta_color == "#16a34a":
        return "#dcfce7"
    elif delta_color == "#dc2626":
        return "#fee2e2"
    return "#f1f5f9"


def get_sparkline_series(df, metric):
    if df is None or df.empty:
        return pd.Series(dtype=float)
    series = df.groupby("date")[metric].mean().round(2)
    series.index = pd.to_datetime(series.index)
    return series


##################################################################
# SATISFACTION LOGIC
# Unsatisfied = ada minimal 1 touchpoint < 3
##################################################################

TOUCHPOINT_COLUMNS = [
    "registration", "doctor_consultation", "nurse_service",
    "pharmacy_service", "laboratory", "emergency_response",
    "billing_process", "facility_cleanliness",
    "staff_friendliness", "waiting_time",
]

def classify_satisfaction(df):
    """
    Klasifikasi tiap pasien:
    - Unsatisfied → ada minimal 1 touchpoint < 3
    - Satisfied   → semua touchpoint >= 3
    Mengembalikan df dengan kolom tambahan 'satisfaction' dan 'gender'
    """
    df = df.copy()
    df["is_unsatisfied"] = df[TOUCHPOINT_COLUMNS].lt(3).any(axis=1)
    df["satisfaction"]   = df["is_unsatisfied"].map(
        {True: "Unsatisfied", False: "Satisfied"}
    )
    return df


def get_satisfaction_counts(df, gender_filter):
    """
    Hitung jumlah Satisfied dan Unsatisfied
    berdasarkan gender yang dipilih via checkbox.
    """
    if not gender_filter:
        return 0, 0

    df_classified = classify_satisfaction(df)
    df_filtered   = df_classified[
        df_classified["gender"].isin(gender_filter)
    ]

    satisfied   = (df_filtered["satisfaction"] == "Satisfied").sum()
    unsatisfied = (df_filtered["satisfaction"] == "Unsatisfied").sum()

    return int(satisfied), int(unsatisfied)


TOUCHPOINT_DISPLAY_NAMES = {
    "registration":        "Registration",
    "doctor_consultation": "Doctor Consultation",
    "nurse_service":       "Nurse Service",
    "pharmacy_service":    "Pharmacy Service",
    "laboratory":          "Laboratory",
    "emergency_response":  "Emergency Response",
    "billing_process":     "Billing Process",
    "facility_cleanliness":"Facility Cleanliness",
    "staff_friendliness":  "Staff Friendliness",
    "waiting_time":        "Waiting Time",
}

def get_touchpoint_complaints(df, gender_filter):
    """
    Hitung jumlah pasien yang memberikan rating < 3
    pada masing-masing touchpoint, difilter berdasarkan gender.
    Mengembalikan list of dict sorted descending by count, max 3 item.
    """
    if not gender_filter or df is None or df.empty:
        return []

    df_filtered = df[df["gender"].isin(gender_filter)].copy()

    results = []
    for col in TOUCHPOINT_COLUMNS:
        count = int((df_filtered[col] < 3).sum())
        if count > 0:
            results.append({
                "touchpoint": TOUCHPOINT_DISPLAY_NAMES[col],
                "count": count,
            })

    results = sorted(results, key=lambda x: x["count"], reverse=True)
    return results[:3]


def get_touchpoint_outcome_heatmap(df, gender_filter):
    """
    Hitung rata-rata outcome (NPS, CSI, Loyalty, CES)
    dari pasien yang memberi rating < 3 pada tiap touchpoint.
    Semakin rendah avg outcome → korelasi buruk lebih kuat → warna lebih gelap.
    Mengembalikan dict: {touchpoint_display_name: {outcome: avg_value}}
    """
    if not gender_filter or df is None or df.empty:
        return {}

    df_filtered = df[df["gender"].isin(gender_filter)].copy()
    outcomes    = ["nps", "csi", "loyalty", "ces"]
    result      = {}

    for col, display_name in TOUCHPOINT_DISPLAY_NAMES.items():
        df_bad = df_filtered[df_filtered[col] < 3]
        if df_bad.empty:
            continue
        result[display_name] = {}
        for outcome in outcomes:
            avg_val = df_bad[outcome].mean()
            result[display_name][outcome.upper()] = round(float(avg_val), 2)

    return result


##################################################################
# CHART
##################################################################

def plot_sparkline(series, color):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=series.index,
            y=series.values,
            mode="lines",
            line=dict(color=color, width=2.5),
            hovertemplate="%{x|%d %b %Y}<br>Value: %{y:.2f}<extra></extra>",
        )
    )
    fig.update_xaxes(visible=False, fixedrange=True)
    fig.update_yaxes(visible=False, fixedrange=True)
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=CHART_HEIGHT,
        margin=dict(t=0, l=0, r=0, b=0),
    )
    return fig


def plot_satisfaction_pie(satisfied, unsatisfied):
    total = satisfied + unsatisfied

    if total == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No data",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="#94a3b8")
        )
        fig.update_layout(
            height=220,
            margin=dict(t=10, l=0, r=0, b=0),
            paper_bgcolor="white",
        )
        return fig

    fig = go.Figure(
        data=go.Pie(
            labels=["Satisfied", "Unsatisfied"],
            values=[satisfied, unsatisfied],
            hole=0.60,
            marker=dict(
                colors=["#22c55e", "#ef4444"],
                line=dict(color="white", width=2)
            ),
            textinfo="none",          # ← sembunyikan teks di slice
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Jumlah: %{value:,}<br>"
                "Persentase: %{percent}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        showlegend=False,             # ← legend dihandle manual di kolom kanan
        height=220,
        margin=dict(t=10, l=0, r=0, b=10),
        paper_bgcolor="white",
        annotations=[dict(
            text=f"<b>{total:,}</b><br><span style='font-size:10px'>Patients</span>",
            x=0.5, y=0.5,
            font=dict(size=15, color="#374151"),
            showarrow=False
        )]
    )

    return fig


##################################################################
# KPI CARD
##################################################################

def display_kpi_card(label, avg_val, delta_str, delta_color, spark_series, key_name):
    badge_bg = get_badge_bg(delta_color)
    if delta_color == "#16a34a":
        line_color = "#16a34a"
    elif delta_color == "#dc2626":
        line_color = "#dc2626"
    else:
        line_color = "#94a3b8"

    with st.container(key=key_name):
        top_left, top_right = st.columns([1.7, 1.3])
        bottom_left, bottom_right = st.columns([1.1, 1])

        with top_left:
            st.markdown(
                f"<div style='font-size:18px; font-weight:700; color:#475569;'>{label}</div>",
                unsafe_allow_html=True
            )

        with top_right:
            st.markdown(
                f"""
                <div style='text-align:right;'>
                    <div style='display:inline-flex; align-items:center; justify-content:center;
                                padding:4px 10px; border-radius:999px;
                                background-color:{badge_bg};
                                color:{delta_color};
                                font-size:15px; font-weight:700;'>
                        {delta_str}
                    </div>
                    <div style='font-size:11px;
                                color:#94a3b8;
                                margin-top:3px;'>
                        vs Prev Month
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with bottom_left:
            st.markdown(f"<div style='height:{LEFT_CONTENT_OFFSET}px;'></div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:13px; color:#94a3b8; font-weight:500;'>Average</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:26px; font-weight:700; color:#000000; margin-top:2px;'>{avg_val:.2f}</div>", unsafe_allow_html=True)

        with bottom_right:
            st.markdown(f"<div style='height:{CHART_VERTICAL_OFFSET}px;'></div>", unsafe_allow_html=True)
            if not spark_series.empty:
                fig = plot_sparkline(spark_series, line_color)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


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
    prev_df = get_previous_period_df(df_branch, start_date, end_date)


##################################################################
# PAGE
##################################################################

st.title("🏥 Always Healthy Hospital Performance")
st.caption("Monitor hospital service performance based on patient survey data.")


##################################################################
# KPI CONFIG & RENDER
##################################################################

KPI_CONFIG = [
    ("NPS",    "nps",     "kpi_nps"),
    ("CSI",    "csi",     "kpi_csi"),
    ("Loyalty","loyalty", "kpi_loyalty"),
    ("CES",    "ces",     "kpi_ces"),
]

cols = st.columns(4)

for col, (label, metric, key_name) in zip(cols, KPI_CONFIG):
    curr_val   = get_kpi_avg(current_df, metric)
    prev_val   = get_kpi_avg(prev_df, metric)
    delta_str, delta_color = get_delta(curr_val, prev_val)
    spark_series = get_sparkline_series(current_df, metric)
    with col:
        display_kpi_card(
            label=label,
            avg_val=curr_val,
            delta_str=delta_str,
            delta_color=delta_color,
            spark_series=spark_series,
            key_name=key_name
        )

##################################################################
# PATIENT SATISFACTION SECTION
##################################################################

sat_col, complaint_col = st.columns([2, 2])

with sat_col:
    with st.container(key="satisfaction_card"):

        # ── Header ───────────────────────────────────────────
        st.markdown(
            "<div style='font-size:15px; font-weight:700; color:#374151; margin-bottom:2px;'>"
                "🏥 Patient Satisfaction"
            "</div>"
            "<div style='font-size:11px; color:#94a3b8; margin-bottom:10px;'>"
                "Unsatisfied = there is at least one touchpoint with a score below 3"
            "</div>",
            unsafe_allow_html=True
        )

        # ── Gender Checkbox ───────────────────────────────────
        male_col, female_col = st.columns(2)

        with male_col:
            st.markdown(
                "<div style='text-align:center;'>"
                "<div style='font-size:44px; line-height:1;'>👨</div>"
                "<div style='font-size:12px; font-weight:600; color:#374151; margin-top:6px;'>Male</div>"
                "</div>",
                unsafe_allow_html=True
            )
            cb1, cb2, cb3 = st.columns([1.05, 0.35, 0.9])
            with cb2:
                show_male = st.checkbox("", value=True, key="cb_male")

        with female_col:
            st.markdown(
                "<div style='text-align:center;'>"
                "<div style='font-size:44px; line-height:1;'>👩</div>"
                "<div style='font-size:12px; font-weight:600; color:#374151; margin-top:6px;'>Female</div>"
                "</div>",
                unsafe_allow_html=True
            )
            cb1, cb2, cb3 = st.columns([1.05, 0.35, 0.9])
            with cb2:
                show_female = st.checkbox("", value=True, key="cb_female")

        # ── Kalkulasi ─────────────────────────────────────────
        gender_filter = []
        if show_male:
            gender_filter.append("Male")
        if show_female:
            gender_filter.append("Female")

        satisfied, unsatisfied = get_satisfaction_counts(current_df, gender_filter)
        total     = satisfied + unsatisfied
        sat_pct   = f"{(satisfied   / total * 100):.1f}%" if total > 0 else "0%"
        unsat_pct = f"{(unsatisfied / total * 100):.1f}%" if total > 0 else "0%"

        # ── Pie + Legend ──────────────────────────────────────
        pie_col, legend_col = st.columns([1.1, 0.9])

        with pie_col:
            fig_pie = plot_satisfaction_pie(satisfied, unsatisfied)
            st.plotly_chart(
                fig_pie,
                use_container_width=True,
                config={"displayModeBar": False}
            )

        with legend_col:
            st.markdown("<div style='height:60px;'></div>", unsafe_allow_html=True)

            LEGEND_X_OFFSET = 53
            LEGEND_Y_OFFSET = -35

            legend_html = (
                f"<div style='display:flex; flex-direction:column; justify-content:center; "
                f"transform: translate({LEGEND_X_OFFSET}px, {LEGEND_Y_OFFSET}px);'>"
                    "<div style='margin-bottom:30px;'>"
                        "<div style='display:flex; align-items:center; gap:10px;'>"
                            "<div style='width:14px; height:14px; border-radius:50%; background:#22c55e;'></div>"
                            "<div style='font-size:15px; font-weight:700; color:#374151;'>Satisfied</div>"
                        "</div>"
                        f"<div style='font-size:28px; font-weight:800; color:#22c55e; "
                        f"margin-left:24px; line-height:1.1;'>{sat_pct}</div>"
                        f"<div style='font-size:13px; color:#94a3b8; "
                        f"margin-left:24px; margin-top:4px;'>{satisfied:,} patients</div>"
                    "</div>"
                    "<div>"
                        "<div style='display:flex; align-items:center; gap:10px;'>"
                            "<div style='width:14px; height:14px; border-radius:50%; background:#ef4444;'></div>"
                            "<div style='font-size:15px; font-weight:700; color:#374151;'>Unsatisfied</div>"
                        "</div>"
                        f"<div style='font-size:28px; font-weight:800; color:#ef4444; "
                        f"margin-left:24px; line-height:1.1;'>{unsat_pct}</div>"
                        f"<div style='font-size:13px; color:#94a3b8; "
                        f"margin-left:24px; margin-top:4px;'>{unsatisfied:,} patients</div>"
                    "</div>"
                "</div>"
            )
            st.markdown(legend_html, unsafe_allow_html=True)

# ── Kolom kanan: Complaint Bar Chart ─────────────────────────────
with complaint_col:
    with st.container(key="complaint_card"):

        st.markdown(
            "<div style='font-size:15px; font-weight:700; "
            "color:#374151; margin-bottom:2px;'>"
                "⚠️ Top Touchpoint Complaints"
            "</div>"
            "<div style='font-size:11px; color:#94a3b8; margin-bottom:16px;'>"
                " "
            "</div>",
            unsafe_allow_html=True
        )

        complaint_data = get_touchpoint_complaints(current_df, gender_filter)
        bar_colors     = ["#1e4640", "#b9f399", "#ebf3e8"]

        if not complaint_data:
            st.markdown(
                "<div style='text-align:center; color:#94a3b8; "
                "font-size:13px; padding:24px 0;'>"
                    "Tidak ada keluhan pada periode ini."
                "</div>",
                unsafe_allow_html=True
            )
        else:
            max_count  = complaint_data[0]["count"]
            items_html = ""

            for i, item in enumerate(complaint_data):
                name      = item["touchpoint"]
                count     = item["count"]
                bar_color = bar_colors[i]
                bar_width = f"{(count / max_count * 100):.1f}%"
                count_str = str(count)

                items_html += (
                    "<div style='margin-bottom:10px;'>"
                        "<div style='font-size:13px; font-weight:600; "
                        "color:#374151; margin-bottom:8px;'>"
                            + name +
                        "</div>"
                        "<div style='display:flex; align-items:center; gap:10px;'>"
                            "<div style='flex:1; background:#f3f4f6; "
                            "border-radius:999px; height:16px; overflow:hidden;'>"
                                "<div style='width:" + bar_width + "; height:100%; "
                                "background:" + bar_color + "; border-radius:999px;'>"
                                "</div>"
                            "</div>"
                            "<div style='font-size:13px; font-weight:700; "
                            "color:#374151; min-width:36px; text-align:right;'>"
                                + count_str +
                            "</div>"
                        "</div>"
                    "</div>"
                )
            st.markdown(items_html, unsafe_allow_html=True)

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    with st.container(key="heatmap_corr_card"):

        st.markdown(
            "<div style='font-size:15px; font-weight:700; "
            "color:#374151; margin-bottom:2px;'>"
                "🔥 Touchpoint Impact"
            "</div>"
            "<div style='font-size:11px; color:#94a3b8; margin-bottom:12px;'>"
                " "
            "</div>",
            unsafe_allow_html=True
        )

        heatmap_data = get_touchpoint_outcome_heatmap(current_df, gender_filter)
        outcomes = ["NPS", "CSI", "LOYALTY", "CES"]

        top_touchpoints = [item["touchpoint"] for item in complaint_data[:3]]

        filtered_heatmap = {
            tp: heatmap_data[tp]
            for tp in top_touchpoints
            if tp in heatmap_data
        }

        if not filtered_heatmap:
            st.markdown(
                "<div style='text-align:center; color:#94a3b8; "
                "font-size:13px; padding:16px 0;'>"
                    "Tidak ada data untuk periode ini."
                "</div>",
                unsafe_allow_html=True
            )
        else:
            touchpoint_names = list(filtered_heatmap.keys())

            all_values = [
                filtered_heatmap[tp].get(o)
                for tp in touchpoint_names
                for o in outcomes
                if heatmap_data[tp].get(o) is not None
            ]

            min_val = min(all_values) if all_values else 0
            max_val = max(all_values) if all_values else 1

            def get_cell_color(value):
                if max_val == min_val:
                    t = 0.5
                else:
                    t = (value - min_val) / (max_val - min_val)

                r = int(30  + t * (185 - 30))
                g = int(70  + t * (243 - 70))
                b = int(64  + t * (153 - 64))

                return f"rgb({r},{g},{b})"

            def get_text_color(value):
                if max_val == min_val:
                    t = 0.5
                else:
                    t = (value - min_val) / (max_val - min_val)

                return "#ffffff" if t < 0.5 else "#1a1a2e"

            # HEADER
            header_cells = "<td style='width:95px;'></td>"

            for outcome in outcomes:
                header_cells += (
                    "<td style='text-align:center; font-size:10px; "
                    "font-weight:700; color:#374151; padding:3px 4px; "
                    "width:52px;'>"
                        + outcome +
                    "</td>"
                )

            rows_html = "<tr>" + header_cells + "</tr>"

            # DATA ROWS
            for tp_name in touchpoint_names:

                row_cells = (
                    "<td style='font-size:10px; font-weight:600; "
                    "color:#374151; padding:3px 6px 3px 0; "
                    "white-space:nowrap;'>"
                        + tp_name +
                    "</td>"
                )

                for outcome in outcomes:
                    val = filtered_heatmap[tp_name].get(outcome)

                    if val is not None:
                        bg_color = get_cell_color(val)
                        txt_color = get_text_color(val)
                        cell_content = str(val)
                    else:
                        bg_color = "#f3f4f6"
                        txt_color = "#9ca3af"
                        cell_content = "—"

                    row_cells += (
                        "<td style='text-align:center; padding:2px;'>"
                            "<div style='"
                                "background:" + bg_color + ";"
                                "color:" + txt_color + ";"
                                "border-radius:8px;"
                                "font-size:10px;"
                                "font-weight:600;"
                                "padding:5px 3px;"
                                "min-width:42px;"
                            "'>"
                                + cell_content +
                            "</div>"
                        "</td>"
                    )

                rows_html += "<tr>" + row_cells + "</tr>"

            table_html = (
                "<div style='overflow-x:auto;'>"
                    "<table style='border-collapse:separate; "
                    "border-spacing:0 2px; width:100%;'>"
                        "<tbody>"
                            + rows_html +
                        "</tbody>"
                    "</table>"
                "</div>"
            )

            st.markdown(table_html, unsafe_allow_html=True)

            st.markdown(
                "<div style='display:flex; align-items:center; gap:8px; "
                "margin-top:10px; justify-content:flex-end;'>"
                    "<div style='font-size:10px; color:#94a3b8;'>Low</div>"
                    "<div style='"
                        "width:70px; height:8px; border-radius:999px;"
                        "background:linear-gradient(to right, #1e4640, #b9f399);"
                    "'></div>"
                    "<div style='font-size:10px; color:#94a3b8;'>High</div>"
                "</div>",
                unsafe_allow_html=True
            )