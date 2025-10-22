from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import os
import pandas as pd
from utils import load_and_clean_excel  # si tu as déjà cette fonction

# 1. Charger et nettoyer les textes
file_path = "data/fiche.xlsx"
texts = load_and_clean_excel(file_path)  # doit renvoyer une liste de textes

# 2. Générer les embeddings
print("🔄 Génération des embeddings...")
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(texts, show_progress_bar=True)

# 3. Sauvegarder les embeddings
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

np.save(os.path.join(OUTPUT_DIR, "embeddings.npy"), embeddings)
print("✅ embeddings.npy sauvegardé dans output/")

# 4. Créer et sauvegarder l’index FAISS
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

faiss.write_index(index, os.path.join(OUTPUT_DIR, "index.faiss"))
print("✅ index.faiss sauvegardé dans output/")

# 5. Sauvegarder aussi les textes alignés avec les embeddings
pd.DataFrame({"text": texts}).to_csv(os.path.join(OUTPUT_DIR, "texts.csv"), index=False)
print("✅ texts.csv sauvegardé dans output/")
