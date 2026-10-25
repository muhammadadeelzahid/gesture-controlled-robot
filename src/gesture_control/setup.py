from glob import glob

from setuptools import find_packages, setup

package_name = "gesture_control"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    tests_require=["pytest"],
    zip_safe=True,
    maintainer="Adeel",
    maintainer_email="adeel.m.zahid@gmail.com",
    description="Maps recognised gestures to TurtleBot3 velocity commands.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "gesture_to_cmd_vel_node = gesture_control.gesture_to_cmd_vel_node:main",
        ],
    },
)
