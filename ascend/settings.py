import sys
import os
import os.path


rcfile_schema = {
    'mixer devicename': (None, str),
    'joystick': 0,
    'hat': 0,
    'move x axis': 0,
    'move y axis': 1,
}

if hasattr(os, "getwindowsversion"):
    rcfile_basename = "lardyarn.txt"
else:
    rcfile_basename = ".lardyarnrc"


def load_settings():
    settings = {}
    for name, value in rcfile_schema.items():
        if isinstance(value, tuple):
            value, _ = value
        settings[name] = value

    rcfile_path = os.path.expanduser("~/" + rcfile_basename)
    if os.path.isfile(rcfile_path):
        with open(rcfile_path, "rt") as f:
            for line in f.read().strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name, equals, value = line.partition("=")
                if not equals:
                    sys.exit("Invalid rcfile line: " + repr(line))
                name = name.strip()
                value = value.strip()
                default = rcfile_schema.get(name)
                if default is None:
                    sys.exit("Invalid value specified in rcfile: " + repr(name))
                if isinstance(default, tuple):
                    default, defaulttype = default
                else:
                    defaulttype = type(default)
                settings[name] = defaulttype(value)
    return settings
