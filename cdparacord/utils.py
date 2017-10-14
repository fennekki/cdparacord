"""Generic useful tools."""
import os

class CdparacordError(Exception):
    pass


def print_error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def sanitise_filename(name):
    return name.replace("/", "-")\
        .replace(": ", " - ")\
        .replace(":", "-")\
        .replace(".", "_")\
        .replace("?", "_")


def find_executable(name, exception):
    ok = False

    for path in os.environ["PATH"].split(os.pathsep):
        path = path.strip('"')
        binname = os.path.join(path, name)
        # isfile checks both that file exists and is a file, os.access
        # with X_OK checks file has executable bit
        if os.path.isfile(binname) and os.access(binname, os.X_OK):
            ok = True
            break

    if ok:
        return binname
    raise exception("{} not found".format(name))


