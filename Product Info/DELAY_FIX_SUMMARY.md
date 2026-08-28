# OvaDue Delay Detection Fix - Summary

## Problem Identified
The delay detection system was not flagging delayed orders because:
1. The "Standard LT" column contains text values like "10 - 16 WK" (weeks), not numeric days
2. The parsing was attempting to convert text strings directly to timedelta, which failed silently
3. All StandardLT values became NaN, so no delays were calculated

## Solution Implemented

### 1. Enhanced Standard LT Parsing
Added intelligent parsing function that:
- Detects "WK" (weeks) notation and converts to days (multiply by 7)
- Extracts first number from format like "10 - 16 WK" → 10 weeks → 70 days
- Falls back to parsing as direct number (for days) if no WK notation
- Returns None for unparseable values (handled gracefully)

### 2. Improved Delay Calculation Logic
- Parses Standard LT to days: "10 - 16 WK" → 70 days
- Calculates BaselineExpectedDeliveryDate = HPReceiveDate + StandardLT
- Calculates DelayDays = PlannedDeliveryDate - BaselineExpectedDeliveryDate
- Flags as delayed when DelayDays > 0
- Converts to DelayWeeks for display (DelayDays / 7)

### 3. Fixed Delayed Orders Filter
- Changed from `df.get("IsDelayed", False)` to proper column check `df["IsDelayed"] == True`
- Ensures filter only applies when column exists

## Test Results
Ran test on osreport_ArupBacklog_2026-08-18_0818.xls:
- Total rows: 80
- **Delayed rows found: 58**
- Non-delayed rows: 22

### Sample Delayed Orders:
| HPReceiveDate | PlannedDeliveryDate | Standard LT | BaselineExpected | DelayDays | DelayWeeks |
|---|---|---|---|---|---|
| 2026-04-14 | 2028-01-13 | 10-16 WK | 2026-06-23 | 569 | 81.3 |
| 2026-08-14 | 2027-02-04 | 6-8 WK | 2026-09-25 | 132 | 18.9 |
| 2026-03-05 | 2026-08-28 | 10-12 WK | 2026-05-14 | 106 | 15.1 |

## Files Modified
- `app.py` - Updated delay calculation logic in `load_all_data()` function (lines 230-277)
- `app.py` - Fixed delayed orders filter in `main()` function (lines 786-789)

## Launch Control Integration
✓ All launch control scripts remain unchanged:
- `launch control.cmd` - Main entry point
- `scripts/OvaDue-LaunchControl.cmd` - Wrapper script
- `scripts/OvaDue-LaunchControl.ps1` - PowerShell controller

The app should be started using: `launch control.cmd` (as before)

## How It Works Now
1. User opens app with: `launch control.cmd`
2. Data loads and delay calculation runs automatically
3. Orders with planned delivery > (order date + lead time) are flagged
4. Visual indicators appear:
   - Red banner above delayed order cards: "Delayed X.X Weeks"
   - Red divider line inside card
5. User can click "Show Delayed Only" button to filter view

## Next Steps
1. Run `launch control.cmd` to start the app
2. Navigate to "My Orders" page
3. Set Region to "Global" and click "Show Delayed Only"
4. Should now see 58+ delayed orders flagged in red
