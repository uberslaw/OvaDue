# OvaDue

OvaDue is a Streamlit dashboard for outstanding orders and delivery-time analysis by office, region, country, and global perspective.

## Run

```powershell
cd "c:\Users\christopher.owen\OneDrive - Arup\Arup\AI\OvaDue"
"C:/Program Files/Python314/python.exe" -m pip install -r requirements.txt
"C:/Program Files/Python314/python.exe" -m streamlit run app.py
```

## Views

- **Outstanding Orders**: laptop quantities awaiting delivery, their current status, planned ship/delivery dates, and late-order detail.
- **Delivery Performance**: planned lead times, requested-date variance, schedule movement, regional/office/country comparisons, and trends across snapshots.
- Manual refresh button and hourly file check for new reports in `uploads\`

## Notes

- Office is shown as a normalized English city extracted from `ShipToAddr`.
- Regions are normalized to `APAC`, `AMR`, `EUR`, and `UKEMEA` using the ship-to country.
- The dashboard detects the browser's timezone and suggests an office in the same timezone when a matching city exists in the data. Select `Filter to same-timezone office` to apply that suggestion. A timezone cannot determine literal proximity; the dashboard does not request browser location.
- Region and office selections are stored in browser local storage and restored on the next visit. Values no longer present in the data are ignored.
- On the first visit in a browser, the dashboard asks the user to select the office cities they want to see. This becomes the default office filter until it is changed in the sidebar.
- Late orders are flagged when `OTD Days` is above threshold and/or `PlannedDeliveryDate` is overdue beyond your grace setting.
- Actual delivery confirmations are not included in the current source reports. Delivery Performance reports first observed `Shipped` status separately from actual delivery, and shows promised versus current planned dates and their movement over time.
- Snapshot date is extracted from filenames like `osreport_ArupBacklog_2026-08-18_0818.xls`.
- Put new `.xls` or `.xlsx` reports in `uploads\`. Open dashboard sessions check the folder hourly; use `Refresh data now` to merge a newly added file immediately.

## Master Launch Control

Register [scripts/OvaDue-LaunchControl.cmd](scripts/OvaDue-LaunchControl.cmd) in Master Launch Control as a `Generic` app. The script is scanable by MLC and opens the Windows Forms operations control for OvaDue.

The Generic card reads [scripts/launch-control.json](scripts/launch-control.json), so its Start, Stop, Restart, status, and Diagnostics controls manage the supervised Streamlit process without requiring a Windows service.
