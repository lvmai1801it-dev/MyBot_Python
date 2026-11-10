import os
import sys

import COCbot.app.paths

# Emulator resolution & DPI settings
WIDTH = "860"
HEIGHT = "732"
DPI = "160"

ADB_BIN = str(COCbot.app.paths.ADB_BIN)

if not os.path.isfile(ADB_BIN):
    print(
        f"❌ Cannot find bundled adb.exe at:\n    {ADB_BIN}\n   Please make sure the entire 'adb' folder sits under src/adb."
    )
    sys.exit(1)
