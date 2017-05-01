# PyRegMonDaemon for Windows - works with Python 2.7 through at least 3.6

A Windows daemon for monitoring and undoing specific shell icon overlay identifier settings that are made by certain applications which cause overlays for other applications to fail to appear.

## __IMPORTANT__: this modifies your Windows registry - DO NOT USE if you aren't comfortable with backing up and editing your registry!

Note: this must run with admin privileges to work properly. You may want to create a shortcut to this that runs minimised with admin privileges, with a target such as:

`C:\Python36\python.exe C:\Users\Username\Desktop\pyregmondaemon.py`

(If you don't make python.exe part of the target you may not be able to check the "run as administrator" box. Alternatively you could run this from an admin-elevated command prompt.)

_You got this far: do I need to remind you to back up your registry? Maybe your whole computer? Do it anyway! Read the code too... if nothing else it's interesting how this works._

## Why this exists:

Windows only offers about 15 shell icon overlay slots. They are allocated
in alphanumeric registry key name order. Programs like TortoiseGit don't
force themselves to appear first in the list, but others applications will
prepend spaces to their key names to use up all the initial slots. This
breaks TortoiseGit's selective overlays as well as those of other apps.
Furthermore, apps that do this often don't allow similarly selective
configuration of their overlays so as to allow them to cooperate with
other apps that the user would prioritize for overlays.

This daemon will immediately and periodically undo specific unwanted
changes to the overlays, preventing such problems in the first place.

Workaround discussions:
    http://stackoverflow.com/questions/25156238/tortoisegit-not-showing-icon-overlays
    https://superuser.com/questions/1042865/can-i-prevent-the-change-of-overlay-icons
    https://cito.github.io/blog/overlay-icon-battle/
    http://stackoverflow.com/questions/20610005/how-to-watch-the-windows-registry-for-changes-with-python
    https://www.dropboxforum.com/t5/Installation-and-desktop-app/STOP-OVERWRITING-MY-ICON-OVERLAY-CONFIGURATION/td-p/186023

More info:
    https://msdn.microsoft.com/en-us/library/windows/desktop/ms724892(v=vs.85).aspx
    https://msdn.microsoft.com/en-us/library/windows/desktop/ms724878(v=vs.85).aspx
    http://docs.activestate.com/activepython/3.4/pywin32/win32api.html
    https://docs.python.org/3.6/library/winreg.html?highlight=winreg#module-winreg

