import importlib
mods = ['pandas', 'xlrd', 'streamlit', 'plotly', 'streamlit_js_eval', 'streamlit_autorefresh', 'openpyxl']
failed = []
for m in mods:
    try: importlib.import_module(m)
    except Exception as e: failed.append('%s: %s' % (m, e))
if failed:
    raise SystemExit('; '.join(failed))
print('ok')
