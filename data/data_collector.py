import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
import csv

class TelemetryCollector(Node):
    def __init__(self):
        super().__init__('telemetry_collector')
        
        # Abonnement au topic IMU de votre véhicule 'hero'
        self.subscription = self.create_subscription(
            Imu,
            '/carla/hero/imu',
            self.imu_callback,
            10)
            
        # Création du fichier CSV pour le dataset d'entraînement
        self.csv_file = open('healthy_driving_data.csv', mode='w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        
        # En-têtes du CSV : Ce sont les "Features" pour votre LSTM
        self.csv_writer.writerow(['timestamp', 'accel_x', 'accel_y', 'accel_z', 'ang_vel_x', 'ang_vel_y', 'ang_vel_z'])
        
        self.get_logger().info('Collecteur ROS 2 démarré. Enregistrement des données physiques en cours...')

    def imu_callback(self, msg):
        # Extraction du temps
        timestamp = msg.header.stamp.sec + (msg.header.stamp.nanosec / 1e9)
        
        # Extraction de l'accélération linéaire (Gère les freinages fantômes)
        ax = msg.linear_acceleration.x
        ay = msg.linear_acceleration.y
        az = msg.linear_acceleration.z
        
        # Extraction de la vitesse angulaire (Gère les changements de voie brusques)
        gx = msg.angular_velocity.x
        gy = msg.angular_velocity.y
        gz = msg.angular_velocity.z
        
        # Sauvegarde de la ligne dans le dataset
        self.csv_writer.writerow([timestamp, ax, ay, az, gx, gy, gz])

def main(args=None):
    rclpy.init(args=args)
    node = TelemetryCollector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('\n Enregistrement terminé. Fichier dataset sauvegardé !')
    finally:
        node.csv_file.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()