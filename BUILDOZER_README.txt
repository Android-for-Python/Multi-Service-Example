# The following changes to buildozer.spec are required:

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3, kivy, oscpy

# (list) List of service to declare
#services = NAME:ENTRYPOINT_TO_PY,NAME2:ENTRYPOINT2_TO_PY
services = Worker_0:service.py:foreground,
           Worker_1:service.py:foreground,
           Worker_2:service.py:foreground,
           Worker_3:service.py:foreground,
           Worker_4:service.py:foreground,
           Worker_5:service.py:foreground,
           Worker_6:service.py:foreground,
           Worker_7:service.py:foreground

# (list) Permissions
android.permissions = INTERNET, FOREGROUND_SERVICE

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86
android.arch = arm64-v8a
