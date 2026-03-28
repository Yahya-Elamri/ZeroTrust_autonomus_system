# CARLA Anomaly Detection : Launching Scripts

This guide provides the complete sequence of commands to start the simulation, the autonomous vehicle, and the security monitoring system.

## 1. Start CARLA Simulator
Open a new terminal and launch the CARLA server.
```bash
cd ~/CARLA_0.9.15
./CarlaUE4.sh -RenderOffScreen
```

## 2. Load Town01 Map
Open a second terminal to configure the environment.
```bash
source /opt/ros/humble/setup.bash
cd ~/CARLA_0.9.15/PythonAPI/util
python3 config.py -m Town01
```

## 3. Generate Background Traffic
Generate 20 vehicles and 10 pedestrians to simulate a realistic urban environment.
```bash
cd ~/CARLA_0.9.15/PythonAPI/examples
python3 generate_traffic.py -n 20 -w 10
```

## 4. Launch Autonomous Ego Vehicle
This command spawns the main vehicle (`hero`) and the ROS 2 bridge. To ensure **Full Autonomy**, we enable the CARLA internal autopilot via a ROS topic.

**Terminal 3:**
```bash
# Setup Environment
source /opt/ros/humble/setup.bash
source ~/carla_ws/install/setup.bash
export CARLA_ROOT=~/CARLA_0.9.15
export PYTHONPATH=$PYTHONPATH:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.15-cp310-cp310-linux_x86_64.egg:$CARLA_ROOT/PythonAPI/carla

# Launch Bridge and Vehicle
ros2 launch carla_ros_bridge carla_ros_bridge_with_example_ego_vehicle.launch.py
```

**Terminal 4 (Enable Autopilot):**
Run this command once the bridge is running to start the automatic driving.
```bash
source /opt/ros/humble/setup.bash
ros2 topic pub /carla/ego_vehicle/enable_autopilot std_msgs/Bool "{data: true}" --once
```

## 5. Launch Plausibility Inference Node (Monitor)
Start the LSTM-based anomaly detector. It will monitor the IMU data for spoofing attacks.
```bash
source /opt/ros/humble/setup.bash
export TF_USE_LEGACY_KERAS=1
cd ~/Desktop/project/LSTM
python3 plausibility_inference_node.py
```

## 6. Security Testing: Launch Attack Injector
To test the system, run the attack injector to simulate an IMU spoofing attack.
```bash
source /opt/ros/humble/setup.bash
cd ~/Desktop/project/attack
python3 attack_injector.py
```

## 7. Visualize in RViz
```bash
source /opt/ros/humble/setup.bash
source ~/carla_ws/install/setup.bash
ros2 run rviz2 rviz2 -d ~/carla_ws/src/ros-bridge/carla_ros_bridge/config/carla_default_rviz.rviz
```