# Handoff: gesture controlled robot

State of the project on 2026-10-25, written for whoever picks it up next, on a laptop, a
workstation or an HPC server.

- Repository: https://github.com/muhammadadeelzahid/gesture_controlled_robot (branch `main`)
- Last commit at handoff: `1e63708 Document the headless demo, training flow and current status`
- CI at that commit: green on every step (lint, build, unit and launch tests, recognition
  launch test with the trained classifier, headless Gazebo smoke test)
- Related docs: [PLAN.md](PLAN.md) (design, work plan, reasoning) and
  [ARCHITECTURE.md](ARCHITECTURE.md) (nodes and topics)

## 1. What the project does

A webcam watches a hand. MediaPipe finds 21 hand landmarks per frame, a classifier turns them
into one of six gesture labels, and a control node maps the label to a velocity command for a
TurtleBot3 burger, simulated in Gazebo or real.

| Label | Action | linear.x (m/s) | angular.z (rad/s) |
|---|---|---|---|
| open_palm, fist | stop | 0 | 0 |
| pointing_up | forward | 0.15 | 0 |
| victory | turn left | 0 | 0.6 |
| thumb_up | turn right | 0 | -0.6 |
| thumb_down | reverse | -0.10 | 0 |

Two interchangeable recognizers, picked at launch with `recognizer:=`:

- `mediapipe`: the stock MediaPipe GestureRecognizer `.task` model, run on the raw image.
- `custom`: a small Keras 3 MLP over the normalised landmarks, exported to `.tflite` and run
  with LiteRT. Trained by the scripts in `ml/`.

## 2. Stack and versions

| Part | Version |
|---|---|
| ROS 2 | Jazzy (Ubuntu 24.04), via the `ros:jazzy` Docker image |
| Simulator | Gazebo Harmonic with the TurtleBot3 Jazzy packages |
| Hand landmarks and stock recognizer | mediapipe 1.1 (has aarch64 and x86_64 wheels) |
| Custom classifier runtime | ai-edge-litert |
| Training | TensorFlow 2.19 or newer, Keras 3.8 or newer (training only, not in the runtime image) |
| Lint | ruff (config in `ruff.toml`, also run by pre-commit) |
| cmd_vel type | `geometry_msgs/TwistStamped` (`use_stamped: true`), which TurtleBot3 on Jazzy expects |

## 3. Repository layout

```
src/
  gesture_msgs/            Gesture.msg: header, label (string), confidence (float32)
  gesture_recognition/
    gesture_recognition/
      hand_landmarker_node.py    image_raw to hand/landmarks (+ hand/image_annotated)
      gesture_classifier_node.py hand/landmarks or image_raw to gesture
      image_sequence_node.py     still images published as image_raw (no camera needed)
      landmarks.py               normalize_landmarks(), MajorityVote
    config/recognition.yaml      node parameters
    launch/recognition.launch.py
    models/                      .task models (downloaded), gesture_mlp.tflite, labels.txt
    test/                        unit tests, recognition launch test, images/ fixtures
  gesture_control/
    gesture_control/
      gesture_to_cmd_vel_node.py gesture to cmd_vel with deadman, ramp and clamp
      velocity.py                pure ramp and clamp logic (unit tested)
    config/gesture_map.yaml      label to velocity table and limits
    launch/bringup.launch.py     whole stack
    launch/camera.launch.py      usb_cam on /dev/video0
    launch/sim.launch.py         TurtleBot3 world in Gazebo
    test/                        velocity unit tests, cmd_vel launch test
ml/
  collect_data.py   webcam or image-folder landmark collection to CSV
  train.py          train the MLP, export .tflite + labels.txt
  evaluate.py       accuracy per class with LiteRT
  common.py         shares normalize_landmarks with the ROS package
  data/seed.csv     seed dataset built from the fixtures
  requirements-train.txt
scripts/
  download_models.sh       fetch the MediaPipe .task files
  headless_smoke_test.sh   Gazebo without GUI, assert /odom moves
  demo_headless.sh         images drive the robot in Gazebo, record a bag, render docs/demo
  plot_demo.py             bag to trajectory.png, timeline.png, demo.gif
  record_bag.sh            record a webcam bag for offline work
docker/                    Dockerfile, docker-compose.yml (services dev and demo)
.github/workflows/ci.yml   CI on ubuntu-24.04 x86_64 inside ros:jazzy
docs/                      PLAN.md, ARCHITECTURE.md, HANDOFF.md, demo/
```

## 4. Data flow

```
usb_cam or image_sequence_node
        |  /image_raw (sensor_msgs/Image)
        v
hand_landmarker_node  ---- /hand/image_annotated (overlay, only when subscribed)
        |  /hand/landmarks (Float32MultiArray, 63 values)
        v
gesture_classifier_node  (custom reads landmarks; mediapipe reads /image_raw directly)
        |  /gesture (gesture_msgs/Gesture)
        v
gesture_to_cmd_vel_node
        |  /cmd_vel (TwistStamped, 20 Hz)
        v
TurtleBot3 in Gazebo, or the real robot with sim:=false
```

Safety behaviour in the control node: the command drops to zero 0.5 s after the last
gesture, speeds ramp at 0.5 m/s^2 and 3.0 rad/s^2, and output is clamped to the burger's
limits of 0.22 m/s and 2.84 rad/s.

Landmark features: subtract the wrist, mirror x for left hands, divide by the largest
absolute coordinate, giving 63 values in the range -1 to 1. The same function is used for
training and at runtime.

Gating: the classifier needs at least 5 of the last 7 frames to agree, with a score of 0.6
or more. The control node ignores gestures below 0.5.

## 5. Quick start

```bash
git clone https://github.com/muhammadadeelzahid/gesture_controlled_robot.git
cd gesture_controlled_robot
scripts/download_models.sh            # not needed if you unpacked the handoff zip
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml run --rm dev
# inside the container
colcon build --symlink-install && source install/setup.bash
pytest -q                             # 13 tests
RECOGNIZER=custom pytest -q src/gesture_recognition/test/test_recognition_launch.py
scripts/headless_smoke_test.sh
scripts/demo_headless.sh              # writes docs/demo/*
```

On a machine with a display and a webcam:

```bash
xhost +local:docker
docker compose -f docker/docker-compose.yml run --rm demo
ros2 launch gesture_control bringup.launch.py recognizer:=mediapipe
ros2 run rqt_image_view rqt_image_view /hand/image_annotated
```

Launch arguments of `bringup.launch.py`:

| Argument | Default | Meaning |
|---|---|---|
| `sim` | `true` | start Gazebo; `false` for the real robot |
| `headless` | `false` | Gazebo server only, no GUI |
| `source` | `camera` | `camera` (usb_cam) or `images` (image_sequence_node) |
| `images` | empty | comma separated files or folders when `source:=images` |
| `recognizer` | `mediapipe` | `mediapipe` or `custom` |

`camera.launch.py` also takes `video_device` (default `/dev/video0`); `sim.launch.py` takes
`x_pose` and `y_pose`.

## 6. What is done and verified

| Item | Where verified |
|---|---|
| colcon build of all three packages | arm64 VM and CI |
| 13 unit and launch tests | arm64 VM and CI |
| Recognition launch test: five fixtures to the right `/gesture` label, `recognizer:=mediapipe` | arm64 VM and CI |
| Same test with `recognizer:=custom` and the committed seed model | arm64 VM and CI |
| Headless Gazebo smoke test, robot moves on `/odom` | arm64 VM and CI |
| Headless demo, images drive the robot, figures in `docs/demo` | arm64 VM, both recognizers |
| Seed model accuracy on its own data (5 classes, 1120 samples) | 0.996 with LiteRT |

## 7. What is not done

These all need a webcam and a display, which the development VM did not have.

1. **Fist fixture.** None of the freely licensed photos tried were detected as a fist. Take
   one webcam frame, add it as `src/gesture_recognition/test/images/fist.jpg`, list it in
   `SOURCES.md` and add `"fist": "fist"` to `EXPECTED` in `test_recognition_launch.py`.
2. **Real dataset.** About 300 samples per class, two or more people, both hands, varied
   light and distance: `python3 ml/collect_data.py --out ml/data/<name>.csv` (keys 0 to 5
   label frames). Keep one person aside as a holdout set.
3. **Retrain on real data** and replace the seed model (section 8).
4. **Live tuning.** Adjust `window`, `min_votes`, `min_confidence` and the speeds. Check that a
   stop lands within 0.5 s and that the robot stays still when the hand leaves the frame.
5. **Gazebo GUI recording** for the README.
6. Optional, in the plan as a stretch goal: an image-based model (MobileNet on HaGRID), the
   only part of the project where an HPC GPU node pays off.

## 8. Training the custom classifier

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r ml/requirements-train.txt
python3 ml/collect_data.py --out ml/data/me.csv                          # webcam
python3 ml/collect_data.py --out ml/data/stills.csv --images photos/ --augment 20
python3 ml/train.py ml/data/*.csv --epochs 100
python3 ml/evaluate.py ml/data/holdout.csv
```

- `--images` wants one sub-folder per label (`photos/fist/*.jpg`, ...).
- `train.py` trains on whichever labels appear in the CSVs and writes `labels.txt` to match,
  so a missing class does not break it.
- Output goes to `src/gesture_recognition/models/`. Rebuild with colcon, then run
  `RECOGNIZER=custom pytest -q src/gesture_recognition/test/test_recognition_launch.py`.
- Lesson learned: collect in VIDEO mode, as `collect_data.py` now does by default
  (`--hold-frames 6`). Landmarks from one-shot detection differ from what the tracker settles
  on, and a model trained on them misread the victory fixture at runtime.
- Keep the TensorFlow install out of the runtime image; only LiteRT is needed there.

## 9. Moving to an HPC server

The handoff zip (`gesture_controlled_robot.zip`, about 22 MB) holds the git history, all
sources, the `.task` models and the trained model. Build output, bags and caches are left out.

```bash
scp gesture_controlled_robot.zip <user>@<login-host>:~/
ssh <user>@<login-host>
unzip gesture_controlled_robot.zip && cd gesture_controlled_robot && git status
```

What runs there and what does not:

| Task | On HPC |
|---|---|
| Training and evaluating the classifier | yes, CPU is enough; a GPU only matters for an image model |
| Build, tests, headless smoke test, headless demo | yes, inside a container |
| Webcam collection, live tuning, GUI demo | no, needs a camera and a display |

Most HPC systems offer Apptainer rather than Docker. Two ways to get the environment:

```bash
# a) build on the cluster from the public base image, then install the rest
apptainer build ros_jazzy.sif docker://ros:jazzy
# b) build the image on a Docker machine of the same CPU architecture and convert it
docker save gesture_controlled_robot:jazzy -o gcr.tar
apptainer build gcr.sif docker-archive://gcr.tar
apptainer exec --bind $PWD:/ws gcr.sif bash -c "cd /ws && colcon build && pytest -q"
```

The image on the development VM is arm64. Most compute nodes are x86_64, so rebuild it there
or on an x86_64 machine rather than copying it. For training alone a plain Python venv with
`ml/requirements-train.txt` is enough; no ROS is needed. Run it as a batch job, for example:

```bash
#!/bin/bash
#SBATCH --job-name=gesture-train
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
source ~/gesture_controlled_robot/.venv/bin/activate
cd ~/gesture_controlled_robot
python3 ml/train.py ml/data/*.csv --epochs 100
python3 ml/evaluate.py ml/data/holdout.csv
```

Check the cluster's own docs for module names, partitions and accounts.

## 10. Conventions and gotchas

- **Word-check hook.** `.git/hooks/wordcheck.sh` runs on commits and rejects certain words,
  arrows, emoji and em-dashes in files and commit messages. The handoff zip carries `.git`
  with the hooks in place; a fresh `git clone` does not, so copy `.git/hooks/` across in that
  case. Run it by hand on changed files before committing.
- **Lint.** `ruff check . && ruff format --check .` must pass; CI enforces it.
- **numpy below 2 in the runtime image.** `constraints.txt` holds numpy at the Ubuntu 24.04
  version because cv_bridge and the other ROS Python bindings are built against it. Any
  package bump in `requirements.txt` must still resolve with that constraint.
- **Models in git.** The `.task` files are ignored (fetch with `scripts/download_models.sh`);
  `gesture_mlp.tflite` and `labels.txt` are committed; `gesture_mlp.keras` is ignored.
- **Bags.** `bags/` is ignored. The annotated image stream is about 15 MB/s, so keep demo
  recordings short. `demo_headless.sh` deletes its bag after plotting unless `KEEP_BAG=1`.
- **Bag recorder in scripts.** Background jobs in a non-interactive shell ignore SIGINT, so
  the demo script stops `ros2 bag record` with `timeout --signal=TERM`.
- **Launch parameters.** `image_sequence_node` takes `images` as one comma separated string,
  because a launch substitution cannot sit inside a string-array parameter.
- **Mirroring.** The landmarker flips frames horizontally (`mirror: true`) so the webcam acts
  like a mirror; training does the same flip.
- **ROS domain.** Compose sets `ROS_DOMAIN_ID=7` by default to avoid crosstalk on shared
  networks.
- **CI warning.** `actions/checkout@v4` triggers a Node.js 20 deprecation notice; harmless
  for now, bump to a newer major when one is out.

## 11. Suggested next steps, in order

1. Laptop session with a webcam: fist fixture, real dataset, live tuning (section 7, items 1
   to 4).
2. Retrain, replace the seed model, confirm CI is green.
3. Record the GUI demo and update the README.
4. Only if the image-model stretch goal is taken up: Apptainer image and SLURM jobs on the
   HPC server for training on HaGRID.
