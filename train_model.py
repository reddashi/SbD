# train_model.py
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import joblib

# Load collected data
df = pd.read_csv("plc_labeled_data.csv")

X = df[["temperature", "moisture", "co2", "light"]]
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

print(f"✅ Accuracy: {clf.score(X_test, y_test) * 100:.2f}%")

joblib.dump(clf, "plc_detector.pkl")
print("💾 Model saved as plc_detector.pkl")
