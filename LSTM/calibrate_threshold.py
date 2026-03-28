import os
os.environ['TF_USE_LEGACY_KERAS'] = '1'

import pandas as pd
import numpy as np
from tensorflow.keras.models import load_model
import joblib
import json

# 1. Load data and scaler
df = pd.read_csv('../data/healthy_driving_data.csv')
features = ['accel_x', 'accel_y', 'accel_z', 'ang_vel_x', 'ang_vel_y', 'ang_vel_z']
data = df[features].values

scaler = joblib.load('scaler.gz')
data_scaled = scaler.transform(data)

# 2. Re-create sequences
def create_sequences(data, time_steps=10):
    xs = []
    for i in range(len(data) - time_steps):
        xs.append(data[i:(i + time_steps)])
    return np.array(xs)

X = create_sequences(data_scaled)

# 3. Load model and predict
model = load_model('plausibility_model.h5')
X_pred = model.predict(X)

# 4. Calculate MSE for each sequence
mse = np.mean(np.power(X - X_pred, 2), axis=(1, 2))

# 5. Determine threshold (99th percentile of training error)
threshold = np.percentile(mse, 99)
print(f"Calculated Threshold (99th percentile): {threshold}")

# 6. Save to config.json
config = {
    "threshold": float(threshold),
    "time_steps": 10,
    "features": features,
    "model_path": "plausibility_model.h5",
    "scaler_path": "scaler.gz"
}

with open('config.json', 'w') as f:
    json.dump(config, f, indent=4)

print("Threshold and config saved to 'config.json'")
