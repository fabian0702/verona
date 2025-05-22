package main

import (
	"fmt"
	"io"
	"log"
	"net"
	"sync"
)

type Proxy struct {
	local    string
	remote   string
	useCache bool
	cacheWg  sync.WaitGroup
}

func NewProxy(localPort int, remoteHost string, remotePort int) *Proxy {
	return &Proxy{
		local:   fmt.Sprintf("0.0.0.0:%d", localPort),
		remote:  fmt.Sprintf("%s:%d", remoteHost, remotePort),
		cacheWg: sync.WaitGroup{},
	}
}

// Start starts the proxy server
func (p *Proxy) Start() error {
	listener, err := net.Listen("tcp", p.local)
	if err != nil {
		return fmt.Errorf("failed to start listener: %w", err)
	}

	defer listener.Close()

	log.Printf("Proxy listening on %s, forwarding to %s", p.local, p.remote)

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("Failed to accept connection: %v", err)
			continue
		}

		go p.handleConnection(conn)
	}
}

func (p *Proxy) SetCacheEnabled(enabled bool) {
	if enabled && p.useCache {
		p.useCache = true
		p.cacheWg.Add(1)
	} else {
		p.useCache = false
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
