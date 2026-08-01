# Share the filelist flattening engine between ff and esim

`ff` is implemented as a reusable flattening engine with a thin CLI adapter, while `esim` parses its own TC YAML and invokes the same engine directly. This keeps `ff` independently usable without forcing `esim` to construct shell commands or recover structured failures from process output; the accepted trade-off is that `esim` and the engine must remain package/API compatible.
