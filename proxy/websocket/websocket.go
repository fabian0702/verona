package websocket

import (
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"

	"github.com/fabian0702/verona/proxy/manager"
	"github.com/gorilla/websocket"
)

type Websocket struct {
	SocketPath string
	Manager    *manager.Manager
}

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

type Command struct {
	CommandType string `json:"type"`
	Data        string `json:"data"`
}

type UnPauseCommand struct {
	ProxyID string `json:"proxy_id"`
	Pause   bool   `json:"pause"`
}

type StartProxy struct {
	ProxyID    string `json:"proxy_id"`
	RemoteHost string `json:"remote_host"`
	RemotePort int    `json:"remote_port"`
	LocalPort  int    `json:"local_port"`
}

type ChangeDestinationCommand struct {
	ProxyID    string `json:"proxy_id"`
	RemoteHost string `json:"remote_host"`
	RemotePort int    `json:"remote_port"`
}

type StopProxyCommand struct {
	ProxyID string `json:"proxy_id"`
}

func (ws *Websocket) wsHandler(w http.ResponseWriter, r *http.Request) {
	// Upgrade the HTTP connection to a WebSocket connection
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		fmt.Println("Error upgrading:", err)
		return
	}
	defer conn.Close()
	// Listen for incoming messages
	for {
		// Read message from the client
		_, message, err := conn.ReadMessage()
		if err != nil {
			fmt.Println("Error reading message:", err)
			break
		}
		// log.Printf("Received: %s\n", message)

		go ws.handleCommand(message)
		// Send a response back to the client
		err = conn.WriteMessage(websocket.TextMessage, []byte("{\"status\": \"ok\"}"))
		if err != nil {
			fmt.Println("Error writing message:", err)
			break
		}
	}
}

func (ws *Websocket) handleCommand(message []byte) {
	var cmd Command
	json.Unmarshal(message, &cmd)

	switch cmd.CommandType {
	case "start_proxy":
		var startProxy StartProxy

		err := json.Unmarshal([]byte(cmd.Data), &startProxy)
		if err != nil {
			fmt.Println("Error unmarshalling start_proxy command:", err)
			return
		}

		log.Printf("Starting proxy with ID: %s, Remote Host: %s, Remote Port: %d, Local Port: %d\n", startProxy.ProxyID, startProxy.RemoteHost, startProxy.RemotePort, startProxy.LocalPort)

		err = ws.Manager.StartProxy(startProxy.ProxyID, startProxy.LocalPort, startProxy.RemoteHost, startProxy.RemotePort)
		if err != nil {
			fmt.Println("Error executing start_proxy command:", err)
			return
		}

	case "stop_proxy":
		var stopProxy StopProxyCommand

		err := json.Unmarshal([]byte(cmd.Data), &stopProxy)
		if err != nil {
			fmt.Println("Error unmarshalling stop_proxy command:", err)
			return
		}

		log.Printf("Stopping proxy with ID: %s\n", stopProxy.ProxyID)

		err = ws.Manager.StopProxy(stopProxy.ProxyID)
		if err != nil {
			fmt.Println("Error executing stop_proxy command:", err)
			return
		}

	case "change_destination":
		var changeDestination ChangeDestinationCommand

		err := json.Unmarshal([]byte(cmd.Data), &changeDestination)
		if err != nil {
			fmt.Println("Error unmarshalling change_destination command:", err)
			return
		}

		log.Printf("Changing destination for proxy with ID: %s, Remote Host: %s, Remote Port: %d\n", changeDestination.ProxyID, changeDestination.RemoteHost, changeDestination.RemotePort)

		err = ws.Manager.ChangeDestination(changeDestination.ProxyID, changeDestination.RemoteHost, changeDestination.RemotePort)
		if err != nil {
			fmt.Println("Error executing change_destination command:", err)
			return
		}

	case "unpause_proxy":
		var unpauseCommand UnPauseCommand

		err := json.Unmarshal([]byte(cmd.Data), &unpauseCommand)
		if err != nil {
			fmt.Println("Error unmarshalling unpause command:", err)
			return
		}

		log.Printf("Unpausing proxy with ID: %s, Pause: %t\n", unpauseCommand.ProxyID, unpauseCommand.Pause)

		err = ws.Manager.UnPauseProxy(unpauseCommand.ProxyID, unpauseCommand.Pause)
		if err != nil {
			fmt.Println("Error executing unpause_proxy command:", err)
			return
		}

	default:
		fmt.Println("Unknown command type:", cmd.CommandType)
	}
}

func (ws *Websocket) Start() {
	http.HandleFunc("/ws", ws.wsHandler)
	log.Printf("Server binding to %s", ws.SocketPath)
	// Remove socket if it already exists
	if _, err := os.Stat(ws.SocketPath); err == nil {
		if err := os.Remove(ws.SocketPath); err != nil {
			log.Printf("Error removing existing socket: %v\n", err)
			return
		}
	}

	// Create Unix socket listener
	listener, err := net.Listen("unix", ws.SocketPath)
	if err != nil {
		log.Printf("Error creating Unix socket: %v\n", err)
		return
	}

	// Set permissions for the socket
	if err := os.Chmod(ws.SocketPath, 0666); err != nil {
		log.Printf("Error setting socket permissions: %v\n", err)
		return
	}

	log.Printf("WebSocket server started on Unix socket: %s\n", ws.SocketPath)

	server := &http.Server{}
	if err := server.Serve(listener); err != nil {
		log.Printf("Error starting server: %v\n", err)
	}
}

func NewWebsocket(socketPath string, manager *manager.Manager) *Websocket {
	return &Websocket{
		SocketPath: socketPath,
		Manager:    manager,
	}
}
