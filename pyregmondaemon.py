
'''
-------------------------------------------------------------------------------
A Windows daemon for monitoring and undoing specific shell icon overlay
identifier settings that are made by certain applications which cause overlays
for other applications to fail to appear.

Note: this must run with admin privileges to work properly

Disclaimer: this modifies your registry - DO NOT USE if you aren't comfortable
with editing your registry!

-------------------------------------------------------------------------------
    Copyright 2017 Martin F. Falatic

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

-------------------------------------------------------------------------------
Why this exists:
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

-------------------------------------------------------------------------------
Notable shell icon overlays that order themselved first by prepending spaces:
    DropboxExt01 Synced! - (green)
    DropboxExt02 Sync in progress (blue)
    DropboxExt03 Locked: Synced! (green + lock)
    DropboxExt04 Locked: Sync in progress (blue + lock)
    DropboxExt05 Sync not happening (red X) [useful]
    DropboxExt06 Locked: Sync not happening (red X + Lock) [useful]
    DropboxExt07 A file or folder isn't syncing (gray minus) [useful]
    DropboxExt08 Locked: A file or folder isn't syncing (gray minus + Lock)
    DropboxExt09 ?
    DropboxExt10 ?

    SkyDrivePro1 ErrorConflict [useful]
    SkyDrivePro2 SyncInProgress
    SkyDrivePro3 InSync

-------------------------------------------------------------------------------
'''

import win32api
import win32event
import win32con
import logging
import time
import re
import sys

class RegMon(object):
    @staticmethod
    def stringToHive(name):
        hive_names = {
            "HKEY_CLASSES_ROOT":   win32con.HKEY_CLASSES_ROOT,
            "HKCR":                win32con.HKEY_CLASSES_ROOT,
            "HKEY_CURRENT_USER":   win32con.HKEY_CURRENT_USER,
            "HKCU":                win32con.HKEY_CURRENT_USER,
            "HKEY_LOCAL_MACHINE":  win32con.HKEY_LOCAL_MACHINE,
            "HKLM":                win32con.HKEY_LOCAL_MACHINE,
            "HKEY_USERS":          win32con.HKEY_USERS,
            "HKU":                 win32con.HKEY_USERS,
            "HKEY_CURRENT_CONFIG": win32con.HKEY_CURRENT_CONFIG,
            "HKCC":                win32con.HKEY_CURRENT_CONFIG,
        }
        if name in hive_names:
            return hive_names[name]
        else:
            return None

    def __init__(self, full_key):
        self.reg_handle = None
        self.evt_handle = None
        self.watching = False
        self.logfile = 'pyregmondaemon.log'
        self.last_sweep_time = 0
        self.event_timeout = 1000   # ms (don't use win32event.INFINITE)
        self.periodic_sweep = 5*60  # s
        self.full_key = full_key
        (reg_hive, reg_key) = self.full_key.split('\\', 1)
        self.reg_hive = self.stringToHive(reg_hive)
        self.reg_key = reg_key
        self.start_logging('pyregmondaemon')

    def __del__(self):
        self.stop_watching()
        self.stop_logging()

    def start_logging(self, log_title):
        self.log = logging.getLogger(log_title)
        self.log.setLevel(logging.DEBUG)
        log_formatter = logging.Formatter('%(asctime)s,%(msecs)03d %(levelname)-5.5s [%(name)s] %(message)s')
        log_fh = logging.FileHandler(self.logfile)
        log_fh.setLevel(logging.DEBUG)
        log_fh.setFormatter(log_formatter)
        self.log.addHandler(log_fh)
        log_ch = logging.StreamHandler(sys.stdout)
        log_ch.setLevel(logging.DEBUG)
        log_ch.setFormatter(log_formatter)
        self.log.addHandler(log_ch)
        self.log.info('='*78)
        self.log.info("Starting monitoring of {:s}".format(self.full_key))

    def stop_logging():
        self.log.info("Ending monitoring")
        for handler in self.log.handlers:
            handler.close()
            self.log.removeFilter(handler)

    def start_watching(self):
        if self.watching:
            return
        self.watching = True
        self.reg_handle = win32api.RegOpenKeyEx(self.reg_hive, self.reg_key, 0, win32con.KEY_NOTIFY)
        self.evt_handle = win32event.CreateEvent(None, 0, 0, None)
        win32api.RegNotifyChangeKeyValue(
            self.reg_handle,
            True,  # subtree changes too
            win32api.REG_NOTIFY_CHANGE_LAST_SET | win32api.REG_NOTIFY_CHANGE_NAME,
            self.evt_handle,  # what happens when triggered (req'd for async)
            True  # async
        )

    def stop_watching(self):
        '''Important before handling events if changing same keys!'''
        if not self.watching:
            return
        win32api.RegCloseKey(self.reg_handle)
        win32api.CloseHandle(self.evt_handle)
        self.watching = False

    def wait_for_event(self):
        if not self.watching:
            self.start_watching()
        ret_code = win32event.WaitForSingleObject(self.evt_handle, self.event_timeout)
        if ret_code == win32event.WAIT_TIMEOUT:
            if time.time() - self.last_sweep_time > self.periodic_sweep:
                self.stop_watching()
                self.sweep_keys()  # periodic failsafe pass
                self.last_sweep_time = time.time()
                self.start_watching()
        else:
            self.stop_watching()
            time.sleep(1)  # Wait a moment = keys may have been in flux
            self.sweep_keys()
            self.start_watching()

    def sweep_keys(self):
        reg_handle_local = win32api.RegOpenKeyEx(
            self.reg_hive,
            self.reg_key,
            0,
            win32con.KEY_ALL_ACCESS
        )
        matched_sub_keys = []
        try:
            key_idx = 0
            while True:
                sub_key = win32api.RegEnumKey(reg_handle_local, key_idx)
                matched_sub_keys.append(sub_key)
                key_idx += 1
        except win32api.error:
            # Easier esp. if things change while looping above
            pass
        for sub_key in matched_sub_keys:
            is_blocked = False
            for searchterm in subkeys_blocked:
                if re.search("^{:s}$".format(searchterm), sub_key):
                    is_blocked = True
                    break
            if is_blocked:
                for searchterm in subkeys_allowed:
                    if re.search("^{:s}$".format(searchterm), sub_key):
                        is_blocked = False
                        break
            if is_blocked:
                logline = r'Deleting key "{:s}\{:s}"'.format(self.full_key, sub_key)
                try:
                    self.log.info(logline)
                    win32api.RegDeleteKey(reg_handle_local, sub_key)
                except win32api.error:
                    # Easier esp. if things change while looping above
                    pass
        win32api.RegCloseKey(reg_handle_local)


if __name__ == "__main__":

    # There should be NO reason to change this value!
    fullkey_watched = r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\ShellIconOverlayIdentifiers'

    subkeys_blocked = [   # The initial block list
        # Will have ^ and $ added programatically
        r'.*\s*DropboxExt.*',
        r'.*\s*SkyDrivePro.*',
    ]

    subkeys_allowed = [  # Exceptions to the block list
        # Will have ^ and $ added programatically
        r'.*\s*DropboxExt05', r'.*\s*DropboxExt5',
        r'.*\s*DropboxExt06', r'.*\s*DropboxExt6',
        r'.*\s*DropboxExt07', r'.*\s*DropboxExt7',
        r'.*\s*SkyDrivePro1',
    ]

    regmon = RegMon(fullkey_watched)
    if not (regmon.reg_hive and regmon.reg_key):
        sys.exit(1)
    while True:
        regmon.wait_for_event()
    regmon.stop_watching()
