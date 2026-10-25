# ROS 2 Jazzy + Gazebo Harmonic + TurtleBot3 + MediaPipe runtime.
# Multi-arch base: builds and runs on arm64 and x86_64.
FROM ros:jazzy

ENV DEBIAN_FRONTEND=noninteractive \
    TURTLEBOT3_MODEL=burger \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-jazzy-ros-gz \
        ros-jazzy-turtlebot3-gazebo \
        ros-jazzy-turtlebot3-teleop \
        ros-jazzy-usb-cam \
        ros-jazzy-cv-bridge \
        ros-jazzy-image-transport \
        ros-jazzy-twist-mux \
        ros-jazzy-rqt-image-view \
        ros-jazzy-launch-testing \
        ros-jazzy-launch-testing-ros \
        python3-pip python3-pytest python3-colcon-common-extensions \
        libportaudio2 libgl1 v4l-utils curl git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt constraints.txt /tmp/
RUN pip install --no-cache-dir -c /tmp/constraints.txt -r /tmp/requirements.txt

# Match the host uid so files in the bind mount keep their owner.
ARG UID=1000
ARG GID=1000
RUN (getent group $GID || groupadd -g $GID dev) \
    && (getent passwd $UID || useradd -m -u $UID -g $GID -s /bin/bash dev) \
    && U=$(getent passwd $UID | cut -d: -f1) \
    && usermod -aG video,sudo $U \
    && echo "$U ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-dev

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
USER $UID
WORKDIR /ws
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
