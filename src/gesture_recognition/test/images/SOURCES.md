# Test images

Used by the recognition launch test and as the seed set for `ml/collect_data.py --images`.
File name = expected label.

| File | Source | License |
|---|---|---|
| pointing_up.jpg, victory.jpg, thumb_up.jpg, thumb_down.jpg | MediaPipe gesture recognizer sample assets, storage.googleapis.com/mediapipe-tasks/gesture_recognizer/ | Google sample assets (Apache 2.0 docs) |
| open_palm.jpg | "Child shows hand with fingers spread in classroom setting during art activity", Shixart1985, Wikimedia Commons | CC BY 2.0 |

No fist image: none of the freely licensed stock photos tried were picked up as a closed fist by the
MediaPipe recognizer (front-on knuckles with no fingers visible). Add one from the webcam collection run.
