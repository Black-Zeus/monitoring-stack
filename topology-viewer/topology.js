/**
 * topology.js - Visualizador de topología de red usando D3.js
 * Carga datos desde /data/topology.json y genera visualización interactiva
 */

class NetworkTopologyViewer {
    constructor() {
        this.svg = d3.select('#topology-svg');
        this.width = 800;
        this.height = 600;
        this.nodes = [];
        this.links = [];
        this.simulation = null;
        this.currentLayout = 'force'; // 'force' o 'hierarchical'

        this.init();
    }

    init() {
        // Configurar SVG
        this.svg.attr('width', this.width).attr('height', this.height);

        // Crear grupos para elementos
        this.linkGroup = this.svg.append('g').attr('class', 'links');
        this.nodeGroup = this.svg.append('g').attr('class', 'nodes');

        // Configurar zoom
        const zoom = d3.zoom()
            .scaleExtent([0.1, 3])
            .on('zoom', (event) => {
                this.nodeGroup.attr('transform', event.transform);
                this.linkGroup.attr('transform', event.transform);
            });

        this.svg.call(zoom);

        // Cargar datos iniciales
        this.loadTopologyData();

        // Auto-refresh cada 5 minutos
        setInterval(() => this.loadTopologyData(), 5 * 60 * 1000);
    }

    async loadTopologyData() {
        try {
            this.updateStatus('🔄', 'Cargando topología...', 'loading');

            // Timeout para la petición
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 segundos

            const response = await fetch('/topology.json', {
                signal: controller.signal,
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                // Intentar con backup si el archivo principal falla
                if (response.status === 404) {
                    console.warn('Archivo topology.json no encontrado, intentando con datos de ejemplo...');
                    this.loadSampleData();
                    return;
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // Verificar que la respuesta sea JSON válido
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('La respuesta no es JSON válido');
            }

            const data = await response.json();

            // Validar estructura de datos
            if (!this.validateTopologyData(data)) {
                throw new Error('Estructura de datos de topología inválida');
            }

            // Procesar y renderizar datos
            this.processTopologyData(data);
            this.renderNetwork();
            this.updateStats();
            this.updateDeviceList();

            // Actualizar timestamp
            const lastUpdate = new Date(data.timestamp || Date.now());
            document.getElementById('lastUpdate').textContent =
                lastUpdate.toLocaleString('es-ES', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                });

            this.updateStatus('🟢', `Topología cargada: ${this.nodes.length} dispositivos, ${this.links.length} conexiones`, 'success');

            // Log para debugging
            console.log('✅ Topología cargada exitosamente:', {
                nodes: this.nodes.length,
                links: this.links.length,
                timestamp: data.timestamp,
                types: this.getNodeTypeStats()
            });

        } catch (error) {
            console.error('❌ Error cargando topología:', error);

            // Manejar diferentes tipos de error
            let errorMessage = 'Error desconocido';

            if (error.name === 'AbortError') {
                errorMessage = 'Timeout - La carga tardó demasiado';
            } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
                errorMessage = 'Error de conexión - Verifique la red';
            } else if (error.message.includes('JSON')) {
                errorMessage = 'Datos corruptos - Archivo JSON inválido';
            } else if (error.message.includes('404')) {
                errorMessage = 'Archivo no encontrado - Ejecute un scan primero';
            } else {
                errorMessage = error.message;
            }

            this.updateStatus('🔴', `Error: ${errorMessage}`, 'error');

            // Cargar datos de ejemplo como fallback
            if (this.nodes.length === 0) {
                console.log('📝 Cargando datos de ejemplo como fallback...');
                this.loadSampleData();
            }
        }
    }

    // Función auxiliar para validar estructura de datos
    validateTopologyData(data) {
        try {
            // Verificar estructura básica
            if (!data || typeof data !== 'object') {
                console.warn('⚠️ Datos de topología no es un objeto válido');
                return false;
            }

            // Verificar que tenga nodos (puede estar vacío)
            if (!Array.isArray(data.nodes)) {
                console.warn('⚠️ Campo "nodes" faltante o no es array');
                data.nodes = []; // Inicializar como array vacío
            }

            // Verificar que tenga enlaces (puede estar vacío)  
            if (!Array.isArray(data.edges)) {
                console.warn('⚠️ Campo "edges" faltante o no es array');
                data.edges = []; // Inicializar como array vacío
            }

            // Validar estructura de nodos
            for (let i = 0; i < data.nodes.length; i++) {
                const node = data.nodes[i];
                if (!node.id) {
                    console.warn(`⚠️ Nodo en índice ${i} sin campo "id", asignando ID automático`);
                    node.id = `node_${i}`;
                }
                if (!node.type) {
                    console.warn(`⚠️ Nodo ${node.id} sin campo "type", asignando "unknown"`);
                    node.type = 'unknown';
                }
                if (!node.label) {
                    node.label = node.id; // Usar ID como label si no existe
                }
            }

            // Validar estructura de enlaces
            for (let i = 0; i < data.edges.length; i++) {
                const edge = data.edges[i];
                if (!edge.source || !edge.target) {
                    console.warn(`⚠️ Enlace en índice ${i} sin source/target válidos, eliminando`);
                    data.edges.splice(i, 1);
                    i--; // Ajustar índice después de eliminar
                    continue;
                }
                if (!edge.type) {
                    edge.type = 'unknown';
                }
            }

            return true;

        } catch (error) {
            console.error('❌ Error validando datos de topología:', error);
            return false;
        }
    }

    // Función auxiliar para obtener estadísticas de tipos de nodos
    getNodeTypeStats() {
        return this.nodes.reduce((stats, node) => {
            stats[node.type] = (stats[node.type] || 0) + 1;
            return stats;
        }, {});
    }

    // Función para cargar datos de ejemplo cuando no hay datos reales
    loadSampleData() {
        console.log('📝 Cargando datos de ejemplo para demostración...');

        const sampleData = {
            timestamp: new Date().toISOString(),
            nodes: [
                {
                    id: "192.168.1.1",
                    type: "gateway",
                    label: "Router Principal"
                },
                {
                    id: "192.168.1.100",
                    type: "host",
                    label: "PC-Escritorio"
                },
                {
                    id: "192.168.1.101",
                    type: "host",
                    label: "Laptop"
                },
                {
                    id: "192.168.1.102",
                    type: "host",
                    label: "Servidor"
                }
            ],
            edges: [
                {
                    source: "192.168.1.1",
                    target: "192.168.1.100",
                    type: "route"
                },
                {
                    source: "192.168.1.1",
                    target: "192.168.1.101",
                    type: "route"
                },
                {
                    source: "192.168.1.1",
                    target: "192.168.1.102",
                    type: "route"
                }
            ]
        };

        // Procesar datos de ejemplo
        this.processTopologyData(sampleData);
        this.renderNetwork();
        this.updateStats();
        this.updateDeviceList();

        // Actualizar timestamp
        document.getElementById('lastUpdate').textContent =
            new Date().toLocaleString('es-ES');

        this.updateStatus('⚠️', 'Mostrando datos de ejemplo - Ejecute un scan para datos reales', 'warning');
    }

    processTopologyData(data) {
        // Procesar nodos
        this.nodes = data.nodes ? data.nodes.map(node => ({
            id: node.id,
            type: node.type || 'host',
            label: node.label || node.id,
            x: Math.random() * this.width,
            y: Math.random() * this.height
        })) : [];

        // Procesar enlaces
        this.links = data.edges ? data.edges.map(edge => ({
            source: edge.source,
            target: edge.target,
            type: edge.type || 'route',
            mac: edge.mac || null
        })) : [];

        // Crear mapa de nodos para referencias rápidas
        this.nodeMap = new Map();
        this.nodes.forEach(node => {
            this.nodeMap.set(node.id, node);
        });
    }

    renderNetwork() {
        if (this.currentLayout === 'force') {
            this.renderForceLayout();
        } else {
            this.renderHierarchicalLayout();
        }
    }

    renderForceLayout() {
        // Configurar simulación de fuerzas
        this.simulation = d3.forceSimulation(this.nodes)
            .force('link', d3.forceLink(this.links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(30));

        this.renderElements();

        // Iniciar simulación
        this.simulation.on('tick', () => {
            this.linkGroup.selectAll('.link')
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            this.nodeGroup.selectAll('.node')
                .attr('transform', d => `translate(${d.x},${d.y})`);
        });
    }

    renderHierarchicalLayout() {
        // Encontrar nodos gateway como raíz
        const gateways = this.nodes.filter(n => n.type === 'gateway');
        const root = gateways.length > 0 ? gateways[0] : this.nodes[0];

        if (!root) return;

        // Crear jerarquía simple
        const hierarchy = this.buildHierarchy(root);
        const treeLayout = d3.tree()
            .size([this.width - 100, this.height - 100]);

        const rootNode = d3.hierarchy(hierarchy);
        treeLayout(rootNode);

        // Aplicar posiciones
        rootNode.descendants().forEach(d => {
            if (d.data.node) {
                d.data.node.x = d.x + 50;
                d.data.node.y = d.y + 50;
            }
        });

        this.renderElements();
    }

    buildHierarchy(root) {
        const visited = new Set();
        const hierarchy = { node: root, children: [] };

        const buildLevel = (parent, depth = 0) => {
            if (depth > 3) return; // Evitar recursión infinita

            visited.add(parent.node.id);

            this.links
                .filter(link => link.source === parent.node.id || link.source.id === parent.node.id)
                .forEach(link => {
                    const targetId = typeof link.target === 'string' ? link.target : link.target.id;

                    if (!visited.has(targetId)) {
                        const targetNode = this.nodeMap.get(targetId);
                        if (targetNode) {
                            const child = { node: targetNode, children: [] };
                            parent.children.push(child);
                            buildLevel(child, depth + 1);
                        }
                    }
                });
        };

        buildLevel(hierarchy);
        return hierarchy;
    }

    renderElements() {
        // Renderizar enlaces
        const linkSelection = this.linkGroup
            .selectAll('.link')
            .data(this.links, d => `${d.source.id || d.source}-${d.target.id || d.target}`);

        linkSelection.exit().remove();

        const linkEnter = linkSelection.enter()
            .append('line')
            .attr('class', d => `link ${d.type}`)
            .attr('stroke-width', 2)
            .attr('stroke', d => this.getLinkColor(d.type));

        linkSelection.merge(linkEnter);

        // Renderizar nodos
        const nodeSelection = this.nodeGroup
            .selectAll('.node')
            .data(this.nodes, d => d.id);

        nodeSelection.exit().remove();

        const nodeEnter = nodeSelection.enter()
            .append('g')
            .attr('class', d => `node ${d.type}`)
            .call(this.dragBehavior());

        // Círculo del nodo
        nodeEnter.append('circle')
            .attr('r', d => this.getNodeRadius(d.type))
            .attr('fill', d => this.getNodeColor(d.type))
            .attr('stroke', '#333')
            .attr('stroke-width', 2);

        // Icono del nodo
        nodeEnter.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', '.35em')
            .attr('font-size', '16px')
            .attr('fill', 'white')
            .text(d => this.getNodeIcon(d.type));

        // Etiqueta del nodo
        nodeEnter.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', '25px')
            .attr('font-size', '12px')
            .attr('fill', '#333')
            .text(d => d.label.length > 15 ? d.label.substring(0, 12) + '...' : d.label);

        // Tooltips
        nodeEnter.append('title')
            .text(d => `${d.type.toUpperCase()}: ${d.label}\nID: ${d.id}`);

        // Eventos
        nodeEnter.on('click', (event, d) => this.onNodeClick(event, d))
            .on('mouseover', (event, d) => this.onNodeHover(event, d))
            .on('mouseout', (event, d) => this.onNodeOut(event, d));

        nodeSelection.merge(nodeEnter);
    }

    dragBehavior() {
        return d3.drag()
            .on('start', (event, d) => {
                if (!event.active && this.simulation) {
                    this.simulation.alphaTarget(0.3).restart();
                }
                d.fx = d.x;
                d.fy = d.y;
            })
            .on('drag', (event, d) => {
                d.fx = event.x;
                d.fy = event.y;
            })
            .on('end', (event, d) => {
                if (!event.active && this.simulation) {
                    this.simulation.alphaTarget(0);
                }
                d.fx = null;
                d.fy = null;
            });
    }

    getNodeColor(type) {
        const colors = {
            gateway: '#FF6B35',
            router: '#4ECDC4',
            host: '#45B7D1',
            switch: '#96CEB4',
            unknown: '#95A5A6'
        };
        return colors[type] || colors.unknown;
    }

    getNodeRadius(type) {
        const sizes = {
            gateway: 20,
            router: 16,
            host: 14,
            switch: 18,
            unknown: 12
        };
        return sizes[type] || sizes.unknown;
    }

    getNodeIcon(type) {
        const icons = {
            gateway: '🌐',
            router: '📡',
            host: '💻',
            switch: '🔀',
            unknown: '❓'
        };
        return icons[type] || icons.unknown;
    }

    getLinkColor(type) {
        const colors = {
            route: '#74C365',
            l2_neighbor: '#3498DB',
            unknown: '#BDC3C7'
        };
        return colors[type] || colors.unknown;
    }

    onNodeClick(event, node) {
        console.log('Nodo seleccionado:', node);

        // Highlight conexiones
        this.highlightConnections(node.id);

        // Mostrar información detallada
        this.showNodeDetails(node);
    }

    onNodeHover(event, node) {
        // Resaltar nodo
        d3.select(event.currentTarget)
            .select('circle')
            .attr('stroke-width', 4)
            .attr('stroke', '#FFD700');
    }

    onNodeOut(event, node) {
        // Quitar resaltado
        d3.select(event.currentTarget)
            .select('circle')
            .attr('stroke-width', 2)
            .attr('stroke', '#333');
    }

    highlightConnections(nodeId) {
        // Resetear estilos
        this.linkGroup.selectAll('.link')
            .attr('stroke-opacity', 0.3)
            .attr('stroke-width', 2);

        this.nodeGroup.selectAll('.node circle')
            .attr('fill-opacity', 0.3);

        // Resaltar conexiones del nodo
        this.linkGroup.selectAll('.link')
            .filter(d => {
                const sourceId = typeof d.source === 'string' ? d.source : d.source.id;
                const targetId = typeof d.target === 'string' ? d.target : d.target.id;
                return sourceId === nodeId || targetId === nodeId;
            })
            .attr('stroke-opacity', 1)
            .attr('stroke-width', 3);

        // Resaltar nodos conectados
        const connectedNodes = new Set([nodeId]);
        this.links.forEach(link => {
            const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
            const targetId = typeof link.target === 'string' ? link.target : link.target.id;

            if (sourceId === nodeId) connectedNodes.add(targetId);
            if (targetId === nodeId) connectedNodes.add(sourceId);
        });

        this.nodeGroup.selectAll('.node circle')
            .filter(d => connectedNodes.has(d.id))
            .attr('fill-opacity', 1);

        // Auto-reset después de 3 segundos
        setTimeout(() => {
            this.linkGroup.selectAll('.link')
                .attr('stroke-opacity', 1)
                .attr('stroke-width', 2);
            this.nodeGroup.selectAll('.node circle')
                .attr('fill-opacity', 1);
        }, 3000);
    }

    showNodeDetails(node) {
        // Por ahora, solo console.log
        // Podrías implementar un modal o panel lateral
        const connections = this.links.filter(link => {
            const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
            const targetId = typeof link.target === 'string' ? link.target : link.target.id;
            return sourceId === node.id || targetId === node.id;
        });

        console.log(`Detalles de ${node.label}:`, {
            id: node.id,
            type: node.type,
            connections: connections.length,
            connectedTo: connections.map(c => {
                const sourceId = typeof c.source === 'string' ? c.source : c.source.id;
                const targetId = typeof c.target === 'string' ? c.target : c.target.id;
                return sourceId === node.id ? targetId : sourceId;
            })
        });
    }

    updateStats() {
        const devicesByType = this.nodes.reduce((acc, node) => {
            acc[node.type] = (acc[node.type] || 0) + 1;
            return acc;
        }, {});

        document.getElementById('deviceCount').textContent = this.nodes.length;
        document.getElementById('connectionCount').textContent = this.links.length;
        document.getElementById('gatewayCount').textContent = devicesByType.gateway || 0;
    }

    updateDeviceList() {
        const deviceList = document.getElementById('deviceList');
        deviceList.innerHTML = '';

        // Agrupar por tipo
        const devicesByType = this.nodes.reduce((acc, node) => {
            if (!acc[node.type]) acc[node.type] = [];
            acc[node.type].push(node);
            return acc;
        }, {});

        Object.entries(devicesByType).forEach(([type, devices]) => {
            const typeGroup = document.createElement('div');
            typeGroup.className = 'device-type-group';

            const typeHeader = document.createElement('h4');
            typeHeader.textContent = `${type.toUpperCase()} (${devices.length})`;
            typeHeader.style.color = this.getNodeColor(type);
            typeGroup.appendChild(typeHeader);

            devices.forEach(device => {
                const deviceItem = document.createElement('div');
                deviceItem.className = 'device-item';
                deviceItem.innerHTML = `
                    <span class="device-icon">${this.getNodeIcon(device.type)}</span>
                    <span class="device-name">${device.label}</span>
                `;
                deviceItem.onclick = () => this.focusOnNode(device.id);
                typeGroup.appendChild(deviceItem);
            });

            deviceList.appendChild(typeGroup);
        });
    }

    focusOnNode(nodeId) {
        const node = this.nodes.find(n => n.id === nodeId);
        if (!node) return;

        // Centrar vista en el nodo
        const transform = d3.zoomIdentity
            .translate(this.width / 2 - node.x, this.height / 2 - node.y)
            .scale(1.5);

        this.svg.transition()
            .duration(750)
            .call(d3.zoom().transform, transform);

        // Simular click en el nodo
        setTimeout(() => {
            this.highlightConnections(nodeId);
        }, 750);
    }

    toggleLayout() {
        this.currentLayout = this.currentLayout === 'force' ? 'hierarchical' : 'force';

        // Parar simulación actual si existe
        if (this.simulation) {
            this.simulation.stop();
        }

        this.renderNetwork();
        console.log(`Layout cambiado a: ${this.currentLayout}`);
    }

    updateStatus(indicator, message, type) {
        const statusElement = document.getElementById('status');
        const indicatorElement = statusElement.querySelector('.status-indicator');
        const messageElement = statusElement.querySelector('span:last-child');

        indicatorElement.textContent = indicator;
        messageElement.textContent = message;

        statusElement.className = `status ${type}`;
    }
}

// Funciones globales para la interfaz
function refreshTopology() {
    if (window.topologyViewer) {
        window.topologyViewer.loadTopologyData();
    }
}

function toggleLayout() {
    if (window.topologyViewer) {
        window.topologyViewer.toggleLayout();
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.topologyViewer = new NetworkTopologyViewer();
    console.log('🌐 Network Topology Viewer inicializado');
});