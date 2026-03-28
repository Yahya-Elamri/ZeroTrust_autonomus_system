import os
os.environ['TF_USE_LEGACY_KERAS'] = '1'

import pandas as pd
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, RepeatVector, TimeDistributed
from sklearn.preprocessing import StandardScaler
import joblib

# 1. Chargement du dataset collecté sur CARLA
df = pd.read_csv('../data/healthy_driving_data.csv')
features = ['accel_x', 'accel_y', 'accel_z', 'ang_vel_x', 'ang_vel_y', 'ang_vel_z']
data = df[features].values

# 2. Normalisation (Critique pour le Zero-Trust)
scaler = StandardScaler()
data_scaled = scaler.fit_transform(data)
joblib.dump(scaler, 'scaler.gz') # Sauvegarde pour le nœud de détection

# 3. Création de séquences (Fenêtre glissante de 10 timesteps)
def create_sequences(data, time_steps=10):
    xs = []
    for i in range(len(data) - time_steps):
        xs.append(data[i:(i + time_steps)])
    return np.array(xs)

X_train = create_sequences(data_scaled)

# 4. Architecture Auto-encodeur LSTM (Détection d'anomalies)
model = Sequential([
    # Encodeur
    LSTM(32, activation='relu', input_shape=(X_train.shape[1], X_train.shape[2]), return_sequences=False),
    RepeatVector(X_train.shape[1]),
    # Décodeur
    LSTM(32, activation='relu', return_sequences=True),
    TimeDistributed(Dense(X_train.shape[2]))
])

model.compile(optimizer='adam', loss='mse')
model.summary()

# 5. Entraînement
print(" Entraînement du Moniteur de Plausibilité...")
history = model.fit(X_train, X_train, epochs=20, batch_size=32, validation_split=0.1)

# 6. Sauvegarde du modèle
model.save('plausibility_model.h5')
print(" Modèle sauvegardé sous 'plausibility_model.h5'")