package proxy

import (
	"context"
	"fmt"
	"io"
	"log"
	"net"
	"sync"
	"syscall"

	"golang.org/x/sys/unix"
)

type Proxy struct {
	localAddress      string
	remoteAddress     string
	protocol          string
	remoteMutex       sync.RWMutex
	proxyTrafficMutex sync.RWMutex
	isPaused          bool
	pauseStateMutex   sync.Mutex
	listener          net.Listener
	stopExecution     context.CancelFunc
}

func NewProxy(localPort int, remoteHost string, remotePort int, protocol string) *Proxy {
	return &Proxy{
		localAddress:      fmt.Sprintf("0.0.0.0:%d", localPort),
		remoteAddress:     fmt.Sprintf("%s:%d", remoteHost, remotePort),
		protocol:          protocol,
		isPaused:          false,
		pauseStateMutex:   sync.Mutex{},
		remoteMutex:       sync.RWMutex{},
		proxyTrafficMutex: sync.RWMutex{},
		listener:          nil,
		stopExecution:     nil,
	}
}

func (p *Proxy) ChangeDestination(remoteHost string, remotePort int) {
	p.remoteMutex.Lock()
	defer p.remoteMutex.Unlock()

	p.remoteAddress = fmt.Sprintf("%s:%d", remoteHost, remotePort)

	log.Printf("Changed destination to %s", p.remoteAddress)
}

func (p *Proxy) Stop() {
	if p.stopExecution != nil {
		p.stopExecution()
	}

	if p.listener != nil {
		p.listener.Close()
	}

	log.Println("Proxy stopped")
}

// Start starts the proxy server
func (p *Proxy) Start() error {
	lc := net.ListenConfig{
		Control: func(network, address string, c syscall.RawConn) error {
			var opErr error
			err := c.Control(func(fd uintptr) {
				opErr = syscall.SetsockoptInt(int(fd), syscall.SOL_SOCKET, unix.SO_REUSEADDR, 1)
				opErr = syscall.SetsockoptInt(int(fd), syscall.SOL_SOCKET, unix.SO_REUSEPORT, 1)
			})
			if err != nil {
				return err
			}
			return opErr
		},
	}

	ctx, cancel := context.WithCancel(context.Background())
	p.stopExecution = cancel

	// Use the context in Listen - this allows the listener to be cancelled
	listener, err := lc.Listen(ctx, p.protocol, p.localAddress)
	if err != nil {
		return fmt.Errorf("failed to start listener: %w", err)
	}

	p.listener = listener
	log.Printf("Proxy listening on %s, forwarding to %s", p.localAddress, p.remoteAddress)

	go func() {
		defer p.listener.Close()

		for {
			// Accept will return an error when context is cancelled
			conn, err := p.listener.Accept()
			if err != nil {
				if ctx.Err() != nil {
					log.Println("Context cancelled, stopping proxy server")
				} else {
					log.Printf("Accept error: %v", err)
				}
				return
			}

			go p.handleConnection(conn)
		}
	}()

	return nil
}

func (p *Proxy) SetTrafficPaused(paused bool) {
	p.pauseStateMutex.Lock()
	defer p.pauseStateMutex.Unlock()

	if paused && !p.isPaused {
		p.proxyTrafficMutex.Lock()
		p.isPaused = true
		log.Println("Traffic paused")
	} else if !paused && p.isPaused {
		p.proxyTrafficMutex.Unlock()
		p.isPaused = false
		log.Println("Traffic resumed")
	}
}

func (p *Proxy) handleConnection(clientConn net.Conn) {
	defer clientConn.Close()

	// This will block if trafficMu is write-locked
	p.proxyTrafficMutex.RLock()
	defer p.proxyTrafficMutex.RUnlock()

	p.remoteMutex.RLock()
	remote := p.remoteAddress
	p.remoteMutex.RUnlock()

	remoteConn, err := net.Dial(p.protocol, remote)
	if err != nil {
		log.Printf("Failed to connect to remote server: %v", err)
		return
	}
	defer remoteConn.Close()

	// Use context for proper cancellation
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go func() {
		defer cancel()
		io.Copy(remoteConn, clientConn)
	}()

	go func() {
		defer cancel()
		io.Copy(clientConn, remoteConn)
	}()

	<-ctx.Done()
}
