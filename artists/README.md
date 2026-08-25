# Local artist lists

The CLI/TUI is the primary way to manage playlists and artist lists:

```powershell
.\.venv\Scripts\python.exe build_playlists.py --tui
```

The playlist editor can create, rename, edit, delete, and save playlist files. Direct `.txt` editing is also supported when you need to make manual changes.

Each `.txt` file represents one playlist, and its filename becomes the playlist name.

Example file contents:

```text
Radiohead
https://music.youtube.com/@radiohead
Radiohead | https://music.youtube.com/channel/UCq19-LqvG35A-30oyAiPiqA
```

Artist list files are intentionally ignored by Git. Keep personal lists local and do not commit them.
