package manager

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/fabian0702/verona/proxy/proxy"
)

type Manager struct {
	proxies map[string]*proxy.Proxy
	mu      sync.RWMutex // Add mutex for thread safety
}

func NewManager() *Manager {
	return &Manager{
		proxies: make(map[string]*proxy.Proxy),
	}
}

func (m *Manager) StartProxy(id string, localPort int, remoteHost string, remotePort int, protocol string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.proxies[id]; exists {
		return fmt.Errorf("proxy with id %s already exists", id)
	}

	p := proxy.NewProxy(localPort, remoteHost, remotePort, protocol)
	if err := p.Start(); err != nil {
		return fmt.Errorf("failed to start proxy: %w", err)
	}

	m.proxies[id] = p
	return nil
}

func (m *Manager) StopProxy(id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if p, ok := m.proxies[id]; ok {
		p.Stop()
		delete(m.proxies, id)
		log.Printf("Proxy %s stopped\n", id)
		return nil
	}

	log.Printf("Proxy %s not found\n", id)
	return fmt.Errorf("proxy with id %s not found", id)
}

func (m *Manager) ChangeDestination(id string, remoteHost string, remotePort int) error {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if p, ok := m.proxies[id]; ok {
		p.ChangeDestination(remoteHost, remotePort)
		return nil
	}
	return fmt.Errorf("proxy with id %s not found", id)
}

func (m *Manager) StopAll() {
	m.mu.Lock()
	defer m.mu.Unlock()

	log.Printf("Stopping all proxies\n")
	for id, p := range m.proxies {
		p.Stop()
		log.Printf("Stopping proxy %s\n", id)
	}
	// Clear the map after stopping all proxies
	m.proxies = make(map[string]*proxy.Proxy)
}

func (m *Manager) StopAllWithTimeout(timeout time.Duration) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	log.Printf("Stopping all proxies with timeout %v\n", timeout)

	// Create a snapshot of proxies to avoid race conditions
	proxies := make(map[string]*proxy.Proxy, len(m.proxies))
	for id, p := range m.proxies {
		proxies[id] = p
	}

	done := make(chan struct{})
	go func() {
		for id, p := range proxies {
			p.Stop()
			log.Printf("Stopping proxy %s\n", id)
		}
		close(done)
	}()

	select {
	case <-done:
		m.proxies = make(map[string]*proxy.Proxy)
		return nil
	case <-ctx.Done():
		// Still clear the map even on timeout since Stop() was called
		m.proxies = make(map[string]*proxy.Proxy)
		return fmt.Errorf("timeout stopping proxies")
	}
}

func (m *Manager) SetPauseState(id string, paused bool) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if p, ok := m.proxies[id]; ok {
		p.SetTrafficPaused(paused)
		status := "resumed"
		if paused {
			status = "paused"
		}
		log.Printf("Proxy %s %s\n", id, status)
		return nil
	}
	return fmt.Errorf("proxy with id %s not found", id)
}

func (m *Manager) ListProxies() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()

	ids := make([]string, 0, len(m.proxies))
	for id := range m.proxies {
		ids = append(ids, id)
	}
	return ids
}

func (m *Manager) ProxyExists(id string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()

	_, exists := m.proxies[id]
	return exists
}
