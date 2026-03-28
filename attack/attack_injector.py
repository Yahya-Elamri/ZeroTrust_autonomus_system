import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu

class AttackInjector(Node):
    def __init__(self):
        super().__init__('attack_injector')
        # We publish to the same IMU topic that the car uses
        # In a real attack, we would "spoof" this data
        self.pub = self.create_publisher(Imu, '/carla/hero/imu', 10)
        self.timer = self.create_timer(0.1, self.inject_fake_data)
        self.get_logger().warn("😈 Attack Injector Ready - Spoofing IMU data...")

    def inject_fake_data(self):
        msg = Imu()
        # Inject physically impossible acceleration to trigger the LSTM detector
        msg.linear_acceleration.x = 100.0 
        msg.linear_acceleration.y = 100.0
        msg.linear_acceleration.z = 100.0
        
        # Publish the fake data
        self.pub.publish(msg)
        self.get_logger().error("🔥 Injecting fake high-acceleration data!")

def main(args=None):
    rclpy.init(args=args)
    node = AttackInjector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Attack stopped.')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()