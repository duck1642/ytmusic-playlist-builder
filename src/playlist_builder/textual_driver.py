"""Textual driver adjustments for the Windows terminal.

Textual's Windows driver enables ``?1003h`` by default. That mode reports
every mouse movement and can overwhelm some Windows terminal/PTY setups.
This project only needs clicks and wheel events, so the custom driver keeps
button-event reporting (``?1000h``) and omits passive movement reporting.
"""

from __future__ import annotations

import sys


if sys.platform == "win32":
    from textual.drivers.windows_driver import WindowsDriver

    class ClickWheelWindowsDriver(WindowsDriver):
        """Windows driver with click-and-wheel mouse reporting only."""

        def _enable_mouse_support(self) -> None:
            if not self._mouse:
                return

            write = self.write
            # Clean up a possibly stale mode from a previous interrupted run.
            write("\x1b[?1003l")
            write("\x1b[?1015l")
            write("\x1b[?1000h")  # Button press/release and wheel events.
            write("\x1b[?1006h")  # SGR extended coordinate encoding.
            self.flush()

        def _disable_mouse_support(self) -> None:
            if not self._mouse:
                return

            write = self.write
            write("\x1b[?1000l")
            write("\x1b[?1006l")
            write("\x1b[?1003l")
            write("\x1b[?1015l")
            self.flush()
else:
    # The Windows module cannot be imported on other platforms. ``App`` accepts
    # None as the driver class and will select its normal platform driver.
    ClickWheelWindowsDriver = None
