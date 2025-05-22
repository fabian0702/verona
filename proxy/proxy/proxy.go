package proxy

import (
	"fmt"
	"io"
	"log"
	"net"
	"sync"
)

type Proxy struct {
	local     string
	remote    string
	UseCache  bool
	cacheWg   sync.WaitGroup
	terminate chan bool
}

func NewProxy(localPort int, remoteHost string, remotePort int) *Proxy {
	return &Proxy{
		local:     fmt.Sprintf("0.0.0.0:%d", localPort),
		remote:    fmt.Sprintf("%s:%d", remoteHost, remotePort),
		cacheWg:   sync.WaitGroup{},
		terminate: make(chan bool),
	}
}

func (p *Proxy) ChangeDestination(remoteHost string, remotePort int) {
	p.remote = fmt.Sprintf("%s:%d", remoteHost, remotePort)
	log.Printf("Changed destination to %s", p.remote)
}
func (p *Proxy) Stop() {
	p.terminate <- true
	log.Println("Proxy stopped")
}

// Start starts the proxy server
func (p *Proxy) Start() error {
	listener, err := net.Listen("tcp", p.local)
	if err != nil {
		return fmt.Errorf("failed to start listener: %w", err)
	}

	log.Printf("Proxy listening on %s, forwarding to %s", p.local, p.remote)

	go func() {
		defer listener.Close()

		for {
			conn, err := listener.Accept()
			if err != nil {
				log.Printf("Failed to accept connection: %v", err)
				continue
			}

			select {
			case <-p.terminate:
				log.Println("Stopping proxy server")
				return
			default:
				go p.handleConnection(conn)
			}
		}
	}()

	return nil
}

func (p *Proxy) SetCacheEnabled(enabled bool) {
	if enabled && !p.UseCache {
		p.UseCache = true
		p.cacheWg.Add(1)
	} else if !enabled && p.UseCache {
		p.UseCache = false
		p.cacheWg.Done()
	}
}

func (p *Proxy) handleConnection(clientConn net.Conn) {
	defer clientConn.Close()

	p.cacheWg.Wait()

	// Connect to the remote server
	remoteConn, err := net.Dial("tcp", p.remote)
	if err != nil {
		log.Printf("Failed to connect to remote server: %v", err)
		return
	}
	defer remoteConn.Close()

	// Create channels to signal when copying is done
	done := make(chan bool, 2)

	// Copy data in both directions
	go func() {
		io.Copy(remoteConn, clientConn)
		done <- true
	}()

	go func() {
		io.Copy(clientConn, remoteConn)
		done <- true
	}()

	// Wait for data copying to complete in either direction
	<-done
}
