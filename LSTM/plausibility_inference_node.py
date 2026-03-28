import os
# CRITICAL: Fix for the environment's Protobuf/TensorFlow conflict
os.environ['TF_USE_LEGACY_KERAS'] = '1'

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import String
import numpy as np
import joblib
from tensorflow.keras.models import load_model
import json
from collections import deque
import csv
import time

class PlausibilityDetector(Node):
    def __init__(self):
        super().__init__('plausibility_detector')
        
        # 1. Configuration & Paths
        base_path = os.path.dirname(__file__)
        config_path = os.path.join(base_path, 'config.json')
        
        # Load calibrated config if exists, otherwise fallback to defaults
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            self.threshold = self.config.get('threshold', 2.5) # Using calibrated 2.52
            self.get_logger().info(f'Loaded calibrated threshold: {self.threshold:.4f}')
        else:
            self.threshold = 1.5 # User fallback
            self.get_logger().warn('Config not found, using default threshold: 1.5')

        # 2. Load model and scaler
        model_path = os.path.join(base_path, 'plausibility_model.h5')
        scaler_path = os.path.join(base_path, 'scaler.gz')
        
        self.model = load_model(model_path)
        self.scaler = joblib.load(scaler_path)
        
        # 3. Sliding window buffer (Efficiency: deque is faster than list.pop(0))
        self.window_size = 10
        self.buffer = deque(maxlen=self.window_size)
        
        # 4. ROS 2 Communication
        self.sub = self.create_subscription(
            Imu, 
            '/carla/hero/imu', 
            self.callback, 
            10)
            
        self.pub = self.create_publisher(
            String, 
            '/security/alerts', 
            10)

        # 5. CSV Logging — enregistrement en temps réel des valeurs MSE
        log_path = os.path.join(base_path, 'mse_log.csv')
        self.csv_file = open(log_path, mode='w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(['timestamp', 'mse', 'threshold', 'status'])
        self.get_logger().info(f'📝 Enregistrement MSE dans : {log_path}')
            
        self.get_logger().info('🛡️ Moniteur Zero-Trust Actif (Zero-Trust Plausibility Monitor active)')

    def callback(self, msg):
        # Extract features (6D IMU)
        current_data = [
            msg.linear_acceleration.x, 
            msg.linear_acceleration.y, 
            msg.linear_acceleration.z,
            msg.angular_velocity.x, 
            msg.angular_velocity.y, 
            msg.angular_velocity.z
        ]
        
        # Normalize sample before adding to buffer
        current_scaled = self.scaler.transform([current_data])[0]
        self.buffer.append(current_scaled)
        
        # Run Zero-Trust check when window is full
        if len(self.buffer) == self.window_size:
            self.run_detection()

    def run_detection(self):
        # Prepare sequence for LSTM (1, 10, 6)
        seq = np.array([list(self.buffer)])
        
        # Reconstruction prediction
        reconstruction = self.model.predict(seq, verbose=0)
        
        # Calculate Error (MSE)
        mse = np.mean(np.power(seq - reconstruction, 2))
        
        # Decision Logic
        if mse > self.threshold:
            status = 'ANOMALIE'
            alert_text = f"🚨 ATTENTION : Anomalie détectée ! MSE: {mse:.4f} (Seuil: {self.threshold:.2f})"
            self.get_logger().error(alert_text)
            self.pub.publish(String(data=alert_text))
        else:
            status = 'NORMAL'
            # Subtle log (don't spam info if you want lean production logs)
            self.get_logger().info(f"Physique OK (MSE: {mse:.4f})", throttle_duration_sec=1.0)

        # Write to CSV log
        self.csv_writer.writerow([time.time(), round(mse, 6), round(self.threshold, 6), status])
        self.csv_file.flush()  # Ensure data is written immediately

def main(args=None):
    rclpy.init(args=args)
    node = PlausibilityDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Monitor shutting down...')
    finally:
        node.csv_file.close()
        node.get_logger().info('📊 Fichier CSV MSE sauvegardé.')
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()