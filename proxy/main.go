package main

import (
	"flag"

	"github.com/fabian0702/verona/proxy/manager"
	"github.com/fabian0702/verona/proxy/websocket"
)

func main() {
	socketPath := flag.String("socket", "/run/verona.sock", "Path to the management unix-socket")
	flag.Parse()

	ws := websocket.NewWebsocket(*socketPath, manager.NewManager())

	ws.Start()
}
