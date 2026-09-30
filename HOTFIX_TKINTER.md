# Windows Matplotlib/Tkinter thread hotfix

The HTTP server handles uploads in worker threads. Report generation uses Matplotlib,
which must not use a GUI backend from those threads. This build forces Matplotlib's
non-GUI `Agg` backend before `pyplot` is imported.

This resolves warnings/errors such as:
- `Starting a Matplotlib GUI outside of the main thread will likely fail`
- `RuntimeError: main thread is not in main loop`
- `Tcl_AsyncDelete: async handler deleted by the wrong thread`

No Tkinter window is required; charts are rendered directly to PNG/PDF files.
