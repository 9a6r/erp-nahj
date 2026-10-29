# Desktop 0.3.0 validation — in progress

These are independent checks of the recovered implementation. Previous 0.2.1 results are historical, not proof of 0.3.0 server behavior. This report remains incomplete until the server workflows below finish.

Environment: official Arch cloud image under unprivileged QEMU/TCG, 4 virtual CPUs, 6 GiB RAM, Linux `7.2.11-zen1-1-zen`, rootless Podman with overlay storage. GTK/WebKit run as the ordinary desktop user with sandboxing enabled. Virtual displays use software rendering and the application graphics compatibility option; this does not measure hardware acceleration.

| Check | Result |
| --- | --- |
| Python regressions | 27 passed, including private state, incomplete backup rejection, locking, safe resume, download integrity and immutable image selection |
| Native server settings | Passed: Arabic/English switching preserves unsaved fields without persisting secrets; active service operations remain visible |
| WebKit on X11 | Passed: visible page, theme, connection, navigation, storage error recovery, stale callbacks and current-page preservation |
| WebKit on Wayland | Same checks passed under headless Weston |
| Native downloads | Saved bytes match; cancellation preserves existing file. Initial portal wait timed out during concurrent package installation under TCG; an independent retry passed |
| Arch package | Build, install, reinstall, remove and runtime dependency check passed; actual saved preferences survived |
| Release server archive | GitHub draft asset 680525902 exists; 1,370,682,143 bytes; SHA256 matches `dc3c5731b34b63865c4e5320f1045f16c46b19dcc7bfaf1522ddc8d71a7553af` |
| Real release download resume | Passed: resumed the final MiB from GitHub with HTTP 206 and verified the complete file SHA256 |
| Local ERPNext setup/data/files/jobs | Pending |
| Database/files/configuration backup | Pending |
| Service and VM restart persistence | Pending |
| External MariaDB TLS and rejection cases | Pending |

The images in `screenshots/0.3.0/zen-*.png` are actual GTK captures from the Zen guest. They show connection and server settings, not a claim that the full server tests have passed. Test databases use disposable validation records; the application creates no demo company or business transactions in a user's site.
