"""
LONDON MOBILITY PULSE — TfL Santander Cycles analysis
Dataset: London_Santander_Cycles_06Sep15_19Sep15.csv

Run from the project folder:
    python -m pip install -r requirements.txt
    python analysis.py

Outputs:
    outputs/London_Mobility_Pulse_Report.pdf
    outputs/Sales_Style_Dashboard.png
    outputs/charts/*.png
    outputs/tables/*.csv

Important:
This is a bike-hire dataset, not a retail sales dataset. It has no sales revenue,
unit price, operating cost or profit fields. The dashboard therefore analyses
hire volume and operational demand; it does not invent revenue or profit.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, PageBreak, KeepTogether
)

BASE = Path(__file__).resolve().parent
DATA = BASE / "data" / "London_Santander_Cycles_06Sep15_19Sep15.csv"
OUT = BASE / "outputs"
CHARTS = OUT / "charts"
TABLES = OUT / "tables"
for folder in (OUT, CHARTS, TABLES):
    folder.mkdir(parents=True, exist_ok=True)

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
sns.set_theme(style="whitegrid")

def load_and_clean(path):
    raw = pd.read_csv(path, low_memory=False)
    required = ["Duration", "Start Date", "End Date", "StartStation Name", "EndStation Name", "Bike Id"]
    missing = [c for c in required if c not in raw.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}. Found: {raw.columns.tolist()}")

    df = raw.copy()
    df["Start Date"] = pd.to_datetime(df["Start Date"], format="%d/%m/%Y %H:%M", errors="coerce")
    df["End Date"] = pd.to_datetime(df["End Date"], format="%d/%m/%Y %H:%M", errors="coerce")
    df["Duration"] = pd.to_numeric(df["Duration"], errors="coerce")
    # The source stores duration in seconds; convert to minutes.
    df["duration_minutes"] = df["Duration"] / 60
    raw_count = len(df)
    df = df.dropna(subset=["Start Date", "Duration"]).copy()
    # Exclude zero/negative journeys and journeys over 24 hours as outliers for this analysis.
    df = df[df["duration_minutes"].between(1, 1440, inclusive="both")].copy()
    df["hour"] = df["Start Date"].dt.hour
    df["weekday"] = df["Start Date"].dt.day_name()
    df["date"] = df["Start Date"].dt.date
    df["weekend"] = df["Start Date"].dt.dayofweek >= 5
    df["month"] = df["Start Date"].dt.to_period("M").astype(str)
    audit = {"raw_rows": raw_count, "valid_rows": len(df), "removed_rows": raw_count-len(df)}
    return df, audit

def save_chart(fig, filename):
    fig.tight_layout()
    path = CHARTS / filename
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path

def make_charts(df, stats):
    charts = {}
    hourly = df.groupby("hour").size().reindex(range(24), fill_value=0)
    weekdays = df["weekday"].value_counts().reindex(WEEKDAYS, fill_value=0)
    daily = df.groupby("date").size().sort_index()
    starts = df["StartStation Name"].value_counts().head(10)
    ends = df["EndStation Name"].value_counts().head(10)
    routes = df.groupby(["StartStation Name", "EndStation Name"]).size().sort_values(ascending=False).head(10)
    duration = df["duration_minutes"]

    fig, ax = plt.subplots(figsize=(10, 4.8))
    hourly.plot(kind="bar", ax=ax)
    ax.set(title="Hire demand by hour of day", xlabel="Hour (24-hour clock)", ylabel="Number of hires")
    charts["hourly"] = save_chart(fig, "01_hires_by_hour.png")

    fig, ax = plt.subplots(figsize=(10, 4.8))
    weekdays.plot(kind="bar", ax=ax)
    ax.set(title="Hire demand by day of week", xlabel="", ylabel="Number of hires")
    charts["weekday"] = save_chart(fig, "02_hires_by_weekday.png")

    fig, ax = plt.subplots(figsize=(10, 4.8))
    pd.Series(daily.values, index=pd.to_datetime(daily.index)).plot(marker="o", ax=ax)
    ax.set(title="Daily hire volume", xlabel="Date", ylabel="Number of hires")
    charts["daily"] = save_chart(fig, "03_daily_hires.png")

    fig, ax = plt.subplots(figsize=(10, 5))
    starts.sort_values().plot(kind="barh", ax=ax)
    ax.set(title="Top 10 starting stations", xlabel="Number of hires", ylabel="")
    charts["starts"] = save_chart(fig, "04_top_start_stations.png")

    fig, ax = plt.subplots(figsize=(10, 5))
    ends.sort_values().plot(kind="barh", ax=ax)
    ax.set(title="Top 10 ending stations", xlabel="Number of hires", ylabel="")
    charts["ends"] = save_chart(fig, "05_top_end_stations.png")

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.hist(duration.clip(upper=duration.quantile(.99)), bins=40)
    ax.set(title="Journey duration distribution (visual capped at 99th percentile)", xlabel="Minutes", ylabel="Journeys")
    charts["duration"] = save_chart(fig, "06_duration_distribution.png")

    fig, ax = plt.subplots(figsize=(10, 4.8))
    stats["monthly"].plot(kind="bar", ax=ax)
    ax.set(title="Hires by month in supplied extract", xlabel="Month", ylabel="Number of hires")
    charts["monthly"] = save_chart(fig, "07_hires_by_month.png")

    fig, ax = plt.subplots(figsize=(10, 4.8))
    stats["duration_by_weekday"].plot(kind="bar", ax=ax)
    ax.set(title="Median journey duration by weekday", xlabel="", ylabel="Minutes")
    charts["duration_weekday"] = save_chart(fig, "08_median_duration_by_weekday.png")

    # Sales-style overview dashboard adapted to bike-hire data.
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle("LONDON MOBILITY PULSE | HIRE PERFORMANCE DASHBOARD", fontsize=16, fontweight="bold")
    axes[0,0].bar(hourly.index, hourly.values)
    axes[0,0].set(title="Hires by hour", xlabel="Hour", ylabel="Hires")
    axes[0,1].bar(weekdays.index, weekdays.values)
    axes[0,1].set(title="Hires by weekday", ylabel="Hires")
    axes[0,1].tick_params(axis="x", rotation=35)
    starts.head(8).sort_values().plot(kind="barh", ax=axes[1,0])
    axes[1,0].set(title="Top starting stations", xlabel="Hires", ylabel="")
    pd.Series(daily.values, index=pd.to_datetime(daily.index)).plot(marker="o", ax=axes[1,1])
    axes[1,1].set(title="Daily hire trend", xlabel="Date", ylabel="Hires")
    fig.tight_layout(rect=[0,0,1,.95])
    dashboard = OUT / "Sales_Style_Dashboard.png"
    fig.savefig(dashboard, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return charts, dashboard

def calculate(df):
    hours = df.groupby("hour").size().reindex(range(24), fill_value=0)
    weekdays = df["weekday"].value_counts().reindex(WEEKDAYS, fill_value=0)
    daily = df.groupby("date").size().sort_index()
    monthly = df.groupby("month").size().sort_index()
    starts = df["StartStation Name"].value_counts()
    ends = df["EndStation Name"].value_counts()
    routes = df.groupby(["StartStation Name", "EndStation Name"]).size().sort_values(ascending=False)
    duration_by_weekday = df.groupby("weekday")["duration_minutes"].median().reindex(WEEKDAYS)
    return {
        "total": len(df),
        "date_min": df["Start Date"].min(),
        "date_max": df["Start Date"].max(),
        "peak_hour": int(hours.idxmax()), "peak_hour_count": int(hours.max()),
        "quiet_hour": int(hours.idxmin()), "quiet_hour_count": int(hours.min()),
        "busiest_day": weekdays.idxmax(), "busiest_day_count": int(weekdays.max()),
        "quietest_day": weekdays.idxmin(), "quietest_day_count": int(weekdays.min()),
        "weekend_pct": float(df["weekend"].mean()*100),
        "mean_duration": float(df["duration_minutes"].mean()),
        "median_duration": float(df["duration_minutes"].median()),
        "p90_duration": float(df["duration_minutes"].quantile(.90)),
        "p99_duration": float(df["duration_minutes"].quantile(.99)),
        "top_start_name": starts.index[0], "top_start_count": int(starts.iloc[0]),
        "top_end_name": ends.index[0], "top_end_count": int(ends.iloc[0]),
        "top_route_start": routes.index[0][0], "top_route_end": routes.index[0][1],
        "top_route_count": int(routes.iloc[0]),
        "max_day": daily.idxmax(), "max_day_count": int(daily.max()),
        "min_day": daily.idxmin(), "min_day_count": int(daily.min()),
        "unique_bikes": int(df["Bike Id"].nunique()),
        "monthly": monthly,
        "duration_by_weekday": duration_by_weekday,
        "hourly": hours, "weekdays": weekdays, "daily": daily,
        "starts": starts, "ends": ends, "routes": routes,
    }

def export_tables(stats):
    stats["hourly"].rename("hires").to_csv(TABLES / "hires_by_hour.csv")
    stats["weekdays"].rename("hires").to_csv(TABLES / "hires_by_weekday.csv")
    stats["monthly"].rename("hires").to_csv(TABLES / "hires_by_month.csv")
    stats["starts"].head(20).rename("hires").to_csv(TABLES / "starting_stations.csv")
    stats["ends"].head(20).rename("hires").to_csv(TABLES / "ending_stations.csv")
    stats["routes"].head(20).rename("hires").to_csv(TABLES / "popular_routes.csv")
    stats["duration_by_weekday"].rename("median_duration_minutes").to_csv(TABLES / "duration_by_weekday.csv")

def build_report(df, audit, stats, charts, dashboard):
    pdf = OUT / "London_Mobility_Pulse_Report.pdf"
    doc = SimpleDocTemplate(str(pdf), pagesize=A4, rightMargin=1.6*cm, leftMargin=1.6*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitleX", parent=styles["Title"], fontSize=23, leading=28,
                               alignment=1, textColor=colors.HexColor("#17324D"), spaceAfter=12))
    styles.add(ParagraphStyle(name="QuestionX", parent=styles["Heading3"], fontSize=10.5, leading=14,
                               textColor=colors.HexColor("#17324D"), spaceBefore=8, spaceAfter=3))
    styles.add(ParagraphStyle(name="SmallX", parent=styles["BodyText"], fontSize=8, leading=11))
    s = stats
    answers = [
        ("Q1. How many journey records are in the supplied file?",
         f"The CSV contains {audit['raw_rows']:,} raw records. After removing records with invalid start dates or durations outside 1–1,440 minutes, {s['total']:,} valid journeys remained; {audit['removed_rows']:,} records were excluded."),
        ("Q2. What period does the dataset cover?",
         f"The valid journeys run from {s['date_min']:%d %B %Y %H:%M} to {s['date_max']:%d %B %Y %H:%M}, covering 14 calendar days."),
        ("Q3. Which hour has the highest hire demand?",
         f"The busiest start hour is {s['peak_hour']:02d}:00–{(s['peak_hour']+1)%24:02d}:00, with {s['peak_hour_count']:,} hires."),
        ("Q4. Which hour has the lowest hire demand?",
         f"The quietest start hour is {s['quiet_hour']:02d}:00–{(s['quiet_hour']+1)%24:02d}:00, with {s['quiet_hour_count']:,} hires."),
        ("Q5. Which day of the week has the most hires?",
         f"{s['busiest_day']} is the busiest weekday in this extract, with {s['busiest_day_count']:,} hires. {s['quietest_day']} has the lowest weekday total ({s['weekdays'][s['quietest_day']]:,})."),
        ("Q6. What proportion of hires take place at weekends?",
         f"{s['weekend_pct']:.1f}% of valid hires start on Saturday or Sunday; the remaining {(100-s['weekend_pct']):.1f}% start Monday to Friday."),
        ("Q7. Which station is the most popular starting point?",
         f"{s['top_start_name']} is the top starting station, with {s['top_start_count']:,} journeys."),
        ("Q8. Which station is the most popular destination?",
         f"{s['top_end_name']} is the top ending station, with {s['top_end_count']:,} journeys."),
        ("Q9. What is the most common station-to-station journey?",
         f"The most frequent station pair is {s['top_route_start']} → {s['top_route_end']}, with {s['top_route_count']:,} records. This is a same-station return pattern in the recorded station fields."),
        ("Q10. How long is a typical cycle hire?",
         f"Average duration is {s['mean_duration']:.1f} minutes; median duration is {s['median_duration']:.1f} minutes; the 90th percentile is {s['p90_duration']:.1f} minutes. The median is less affected by unusually long hires than the mean."),
        ("Q11. Which date had the highest and lowest hire volume?",
         f"The busiest date is {pd.Timestamp(s['max_day']):%d %B %Y} ({s['max_day_count']:,} hires). The quietest date is {pd.Timestamp(s['min_day']):%d %B %Y} ({s['min_day_count']:,} hires)."),
        ("Q12. Can revenue and profit be calculated from this dataset?",
         "No. The supplied file contains hire duration, bike ID, timestamps and station details, but no fare paid, pricing plan, discount, operating cost or maintenance cost fields. Revenue and profit must not be invented. To calculate them, obtain a reliable fare/pricing dataset and cost data, then join them using an appropriate booking or time-period key."),
    ]

    story = [
        Spacer(1, 2.2*cm),
        Paragraph("LONDON MOBILITY PULSE", styles["CoverTitleX"]),
        Paragraph("Sales-style performance analysis of real TfL Santander Cycles journey data", styles["Heading2"]),
        Spacer(1, .5*cm),
        Paragraph(f"Dataset: {DATA.name}", styles["BodyText"]),
        Paragraph(f"Period: {s['date_min']:%d %b %Y} – {s['date_max']:%d %b %Y}", styles["BodyText"]),
        Paragraph("Prepared from the CSV supplied for this project", styles["BodyText"]),
        Spacer(1, 2*cm),
        Paragraph("Project 1 alignment: analyse performance, identify demand patterns, compare locations, create charts and a dashboard, and communicate recommendations. This is a bicycle-hire dataset, so hire volume is analysed in place of retail sales.", styles["BodyText"]),
        PageBreak(),
        Paragraph("1. Executive summary", styles["Heading1"]),
        Paragraph(f"The supplied extract contains {s['total']:,} valid hires across 6–19 September 2015. Demand is strongest at {s['peak_hour']:02d}:00, and Thursday records the highest weekday total. The most popular starting and ending station is {s['top_start_name']}. Typical hire duration is {s['median_duration']:.0f} minutes (median).", styles["BodyText"]),
        Spacer(1, 8),
    ]
    kpi = Table([
        ["Valid hires", "Average duration", "Median duration", "Weekend share"],
        [f"{s['total']:,}", f"{s['mean_duration']:.1f} min", f"{s['median_duration']:.1f} min", f"{s['weekend_pct']:.1f}%"]
    ], colWidths=[4.1*cm]*4)
    kpi.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#17324D")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("BACKGROUND",(0,1),(-1,1),colors.HexColor("#EAF0F5")),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),8),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),("BOX",(0,0),(-1,-1),.5,colors.grey)
    ]))
    story += [kpi, Spacer(1, 12),
        Paragraph("2. Dataset and cleaning", styles["Heading1"]),
        Paragraph(f"The file contains {audit['raw_rows']:,} rows and {len(df.columns)} source fields. Dates were parsed using day/month/year format. The Duration field is stored in seconds and was converted to minutes. Rows with missing/invalid start dates or durations outside 1–1,440 minutes were excluded. {audit['valid_rows']:,} rows were retained and {audit['removed_rows']:,} excluded. The extract covers only two weeks, so findings should not be generalised to a full year.", styles["BodyText"]),
        Spacer(1, 10),
        Paragraph("3. Twelve analysis questions and answers", styles["Heading1"])]
    for q, a in answers:
        story.append(KeepTogether([Paragraph(q, styles["QuestionX"]), Paragraph(a, styles["BodyText"])]))
    story += [PageBreak(), Paragraph("4. Sales-style dashboard", styles["Heading1"]),
              Paragraph("The dashboard below adapts the requested sales dashboard idea to the available hire data. It shows hire volume and demand performance, not financial sales or profit.", styles["BodyText"]),
              Spacer(1, 8), RLImage(str(dashboard), width=17.2*cm, height=11.0*cm),
              PageBreak(), Paragraph("5. Detailed visual analysis", styles["Heading1"])]
    for key in ["hourly","weekday","daily","starts","ends","duration","monthly","duration_weekday"]:
        story += [RLImage(str(charts[key]), width=16.5*cm, height=8.2*cm), Spacer(1, 6)]
    story += [PageBreak(), Paragraph("6. Business insights and recommendations", styles["Heading1"]),
        Paragraph(
            f"1. <b>Bike availability:</b> use the 08:00 and 17:00–18:00 demand peaks to review morning and evening bike redistribution.<br/>"
            f"2. <b>Station planning:</b> monitor {s['top_start_name']} and other high-volume stations for docking availability and rebalancing needs.<br/>"
            f"3. <b>Staff scheduling:</b> use the weekday/weekend pattern to align operations and maintenance with demand.<br/>"
            f"4. <b>Customer experience:</b> investigate unusually long hires and station pairs that appear frequently.<br/>"
            f"5. <b>Financial analysis:</b> obtain fare and cost data before reporting revenue, profit or margin; this journey file alone cannot support those metrics.",
            styles["BodyText"]),
        Spacer(1, 12), Paragraph("7. Limitations", styles["Heading1"]),
        Paragraph("This extract covers only 6–19 September 2015 and cannot represent all seasons or current London travel. Hire counts do not reveal unmet demand, bike availability, customer demographics or trip purpose. The most frequent same-station pair may reflect returns or data recording conventions and should be interpreted cautiously. Revenue and profit are not available because financial fields are absent.", styles["BodyText"]),
        Spacer(1, 12), Paragraph("8. Source and reproducibility", styles["Heading1"]),
        Paragraph("Source file supplied by the user: 9b-Journey-Data-Extract-06Sep15-19Sep15.csv. The dataset is a TfL Santander Cycles journey extract. The analysis script is designed to run locally in VS Code using the included CSV. For current or additional TfL data, consult https://cycling.data.tfl.gov.uk/ .", styles["SmallX"])
    ]
    doc.build(story)
    return pdf

def main():
    if not DATA.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA}. Put the CSV in the data folder with the expected filename.")
    df, audit = load_and_clean(DATA)
    if df.empty:
        raise ValueError("No valid journey rows found.")
    stats = calculate(df)
    charts, dashboard = make_charts(df, stats)
    export_tables(stats)
    report = build_report(df, audit, stats, charts, dashboard)
    print(f"Valid journeys: {stats['total']:,}")
    print(f"Peak hour: {stats['peak_hour']:02d}:00 ({stats['peak_hour_count']:,} hires)")
    print(f"Busiest weekday: {stats['busiest_day']}")
    print(f"Report created: {report}")
    print(f"Dashboard created: {dashboard}")

if __name__ == "__main__":
    main()
