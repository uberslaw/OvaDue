import pandas as pd
from pathlib import Path

files = sorted(Path('.').glob('*.xls'), reverse=True)
if files:
    df = pd.read_excel(files[0])
    cols = list(df.columns)
    print(f'Total columns: {len(cols)}\n')
    print('Last 15 columns:')
    for i, col in enumerate(cols[-15:]):
        idx = len(cols) - 15 + i
        val = df[col].iloc[0] if len(df) > 0 else 'N/A'
        print(f'  [{idx}] {col:30s} = {str(val)[:50]}')

    # Look for columns containing 'lead', 'lt', 'std', 'delay'
    print('\n\nColumns matching lead/delay patterns:')
    for i, col in enumerate(cols):
        if any(x in col.lower() for x in ['lead', 'lt', 'std', 'delay']):
            print(f'  [{i}] {col}')
