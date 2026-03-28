# Utilize a ROS 2 Humble image as base
FROM osrf/ros:humble-desktop-full

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV TF_USE_LEGACY_KERAS=1

# Install Python and essential libraries
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-colcon-common-extensions \
    ros-humble-ros-base \
    && rm -rf /var/lib/apt/lists/*

# Install ML dependencies
RUN pip3 install --no-cache-dir \
    tensorflow==2.20.0 \
    tf-keras==2.20.1 \
    pandas \
    numpy==1.26.4 \
    scipy==1.15.3 \
    scikit-learn \
    joblib

# Create workspace directory
WORKDIR /app

# Copy the project files
COPY . .

# Set up entrypoint for ROS 2
ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]
