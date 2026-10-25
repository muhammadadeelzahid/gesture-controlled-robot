from glob import glob

from setuptools import find_packages, setup

package_name = "gesture_recognition"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
        (
            "share/" + package_name + "/models",
            glob("models/*.task") + glob("models/*.tflite") + glob("models/*.txt"),
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Adeel",
    maintainer_email="adeel.m.zahid@gmail.com",
    description="MediaPipe hand landmarks and gesture classification nodes.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "hand_landmarker_node = gesture_recognition.hand_landmarker_node:main",
            "gesture_classifier_node = gesture_recognition.gesture_classifier_node:main",
        ],
    },
)
