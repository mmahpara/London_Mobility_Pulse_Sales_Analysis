# London Mobility Pulse — Project 1

A sales-dashboard-style data analysis project using the supplied real TfL Santander Cycles journey extract (6–19 September 2015).

## Project files
- `analysis.py`: complete analysis, 12 question answers, charts, dashboard, CSV summaries and PDF report.
- `data/London_Santander_Cycles_06Sep15_19Sep15.csv`: the supplied dataset.
- `requirements.txt`: Python dependencies.
- `outputs/`: generated PDF, dashboard, charts and summary tables.

## Run in VS Code (Windows)
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python analysis.py
```
Open `outputs/London_Mobility_Pulse_Report.pdf` and `outputs/Sales_Style_Dashboard.png`.

## Important data limitation
This is bike-hire data, not retail sales data. It has no price, fare revenue, operating costs or profit fields. The project analyses hire volume and demand. Do not invent revenue or profit figures.
