package manager

import (
	"fmt"
	"log"

	"github.com/fabian0702/verona/proxy/proxy"
)

type Manager struct {
	proxies map[string]*proxy.Proxy
}

func NewManager() *Manager {
	return &Manager{
		proxies: make(map[string]*proxy.Proxy),
	}
}

func (m *Manager) StartProxy(id string, localPort int, remoteHost string, remotePort int) error {
	p := proxy.NewProxy(localPort, remoteHost, remotePort)

	if err := p.Start(); err != nil {
		return fmt.Errorf("failed to start proxy: %w", err)
	}

	m.proxies[id] = p

	return nil
}

func (m *Manager) StopProxy(id string) error {

	if p, ok := m.proxies[id]; ok {
		go p.Stop()

		delete(m.proxies, id)

		log.Printf("Proxy %s stopped\n", id)

		return nil
	}

	log.Printf("Proxy %s not found\n", id)

	return fmt.Errorf("proxy with id %s not found", id)
}

func (m *Manager) ChangeDestination(id string, remoteHost string, remotePort int) error {

	if p, ok := m.proxies[id]; ok {
		p.ChangeDestination(remoteHost, remotePort)
		return nil
	}
	return fmt.Errorf("proxy with id %s not found", id)
}

func (m *Manager) StopAll() {
	log.Printf("Stopping all proxies\n")
	for id, p := range m.proxies {
		p.Stop()
		log.Printf("Stopping proxy %s\n", id)
		delete(m.proxies, id)
	}
}

func (m *Manager) UnPauseProxy(id string, paused bool) error {

	if p, ok := m.proxies[id]; ok {
		p.SetCacheEnabled(paused)
		status := "resumed"
		if paused {
			status = "paused"
		}
		log.Printf("Proxy %s %s\n", id, status)
		return nil
	}
	return fmt.Errorf("proxy with id %s not found", id)
}
