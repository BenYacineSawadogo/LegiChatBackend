import pandas as pd
import re

def clean_text(text):
    if pd.isna(text):
        return ""
    text = re.sub(r'[^a-zA-Z0-9\s]', '', str(text))
    return text.strip()

def load_and_clean_excel(path):
    df = pd.read_excel(path)
    df_clean = df.applymap(lambda x: clean_text(x) if isinstance(x, str) else "")
    texts = df_clean.astype(str).agg(" ".join, axis=1).tolist()
    return texts
