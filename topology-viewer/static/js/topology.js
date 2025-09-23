/**
 * topology-viewer/static/js/topology.js
 * Visualizador de topología de red usando D3.js
 * Carga datos desde /topology.json y genera visualización interactiva
 */

class NetworkTopologyViewer {
    constructor(containerId = 'topology-svg') {
        // Configuración inicial
        this.containerId = containerId;
        this.svg = d3.select(`#${containerId}`);
        this.width = 800;
        this.height = 600;
        this.nodes = [];
        this.links = [];
        this.simulation = null;
        this.currentLayout = 'force'; // 'force' o 'hierarchical'
        
        // Estado interno
        this.nodeMap = new Map();
        this.isInitialized = false;
        this.lastDataUpdate = null;
        this.retryCount = 0;
        this.maxRetries = 3;
        
        // Configuración de colores y tamaños
        this.config = {
            nodes: {
                sizes: {
                    gateway: 20,
                    router: 16,
                    host: 14,
                    switch: 18,
                    unknown: 12
                },
                colors: {
                    gateway: '#FF6B35',
                    router: '#4ECDC4',
                    host: '#45B7D1',
                    switch: '#96CEB4',
                    unknown: '#95A5A6'
                },
                icons: {
                    gateway: '🌐',
                    router: '📡',
                    host: '💻',
                    switch: '🔀',
                    unknown: '❓'
                }
            },
            links: {
                colors: {
                    route: '#74C365',
                    l2_neighbor: '#3498DB',
                    unknown: '#BDC3C7'
                },
                widths: {
                    default: 2,
                    highlighted: 3
                }
            },
            simulation: {
                linkDistance: 100,
                chargeStrength: -300,
                collisionRadius: 30,
                alphaTarget: 0.3
            }
        };

        // Inicializar
        this.init();
    }

    init() {
        console.log('🌐 Initializing NetworkTopologyViewer');
        
        try {
            // Configurar SVG
            this.setupSVG();
            
            // Crear grupos para elementos
            this.createElementGroups();
            
            // Configurar zoom
            this.setupZoom();
            
            // Cargar datos iniciales
            this.loadTopologyData();
            
            // Auto-refresh cada 5 minutos
            this.startAutoRefresh();
            
            this.isInitialized = true;
            console.log('✅ NetworkTopologyViewer initialized successfully');
            
        } catch (error) {
            console.error('❌ Error initializing topology viewer:', error);
            this.showError('Error inicializando visualizador');
        }
    }

    setupSVG() {
        // Obtener dimensiones del contenedor
        const container = this.svg.node().parentElement;
        if (container) {
            const rect = container.getBoundingClientRect();
            this.width = rect.width || 800;
            this.height = rect.height || 600;
        }
        
        this.svg
            .attr('width', this.width)
            .attr('height', this.height)
            .attr('viewBox', `0 0 ${this.width} ${this.height}`)
            .style('background', 'transparent');
            
        console.log(`📐 SVG configured: ${this.width}x${this.height}`);
    }

    createElementGroups() {
        // Limpiar contenido existente
        this.svg.selectAll('*').remove();
        
        // Recrear definiciones
        const defs = this.svg.append('defs');
        
        // Marker para flechas
        defs.append('marker')
            .attr('id', 'arrowhead')
            .attr('markerWidth', 10)
            .attr('markerHeight', 7)
            .attr('refX', 9)
            .attr('refY', 3.5)
            .attr('orient', 'auto')
            .append('polygon')
            .attr('points', '0 0, 10 3.5, 0 7')
            .attr('fill', this.config.links.colors.route);

        // Filtros para efectos
        const filter = defs.append('filter')
            .attr('id', 'drop-shadow')
            .attr('height', '130%');
            
        filter.append('feDropShadow')
            .attr('dx', 2)
            .attr('dy', 2)
            .attr('stdDeviation', 3)
            .attr('flood-opacity', 0.3);

        // Crear grupos principales
        this.linkGroup = this.svg.append('g').attr('class', 'links');
        this.nodeGroup = this.svg.append('g').attr('class', 'nodes');
        
        console.log('📦 Element groups created');
    }

    setupZoom() {
        const zoom = d3.zoom()
            .scaleExtent([0.1, 3])
            .on('zoom', (event) => {
                this.nodeGroup.attr('transform', event.transform);
                this.linkGroup.attr('transform', event.transform);
            });

        this.svg.call(zoom);
        
        // Guardar zoom para uso posterior
        this.zoomBehavior = zoom;
        
        console.log('🔍 Zoom behavior configured');
    }

    async loadTopologyData() {
        const loadingId = window.loadingManager ? window.loadingManager.start('topology') : null;
        
        try {
            this.showLoadingState();
            this.updateStatus('🔄', 'Cargando topología...', 'loading');

            // Configurar timeout para la petición
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);

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
                    console.warn('⚠️ topology.json not found, loading sample data');
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
            this.hideLoadingState();

            // Actualizar timestamp
            this.lastDataUpdate = new Date(data.timestamp || Date.now());
            this.updateLastUpdateDisplay();

            this.updateStatus('🟢', `Topología cargada: ${this.nodes.length} dispositivos, ${this.links.length} conexiones`, 'success');
            this.retryCount = 0; // Reset retry count on success

            // Log para debugging
            console.log('✅ Topology loaded successfully:', {
                nodes: this.nodes.length,
                links: this.links.length,
                timestamp: data.timestamp,
                types: this.getNodeTypeStats()
            });

        } catch (error) {
            console.error('❌ Error loading topology:', error);
            this.handleLoadingError(error);
        } finally {
            if (loadingId && window.loadingManager) {
                window.loadingManager.stop(loadingId);
            }
        }
    }

    handleLoadingError(error) {
        this.retryCount++;
        
        let errorMessage = 'Error desconocido';
        let shouldRetry = false;
        let shouldStopAutoRefresh = false;

        if (error.name === 'AbortError') {
            errorMessage = 'Timeout - La carga tardó demasiado';
            shouldRetry = true;
        } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
            errorMessage = 'Error de conexión - Verifique la red';
            shouldRetry = true;
        } else if (error.message.includes('JSON')) {
            errorMessage = 'Datos corruptos - Archivo JSON inválido';
        } else if (error.message.includes('404')) {
            errorMessage = 'Archivo no encontrado - Ejecute un scan primero';
            shouldStopAutoRefresh = true; // Detener auto-refresh para 404
        } else {
            errorMessage = error.message;
        }

        this.updateStatus('🔴', `Error: ${errorMessage}`, 'error');

        // Si es 404, detener auto-refresh y mostrar mensaje
        if (shouldStopAutoRefresh) {
            console.log('🛑 404 error detected, stopping topology auto-refresh');
            this.stopAutoRefresh();
            this.showTopologyUnavailableMessage();
            this.hideLoadingState();
            return;
        }

        // Retry logic solo para errores recuperables
        if (shouldRetry && this.retryCount < this.maxRetries) {
            console.log(`🔄 Retrying topology load (${this.retryCount}/${this.maxRetries})...`);
            setTimeout(() => this.loadTopologyData(), 5000 * this.retryCount);
            return;
        }

        // Si alcanzó max retries, detener auto-refresh también
        if (this.retryCount >= this.maxRetries) {
            console.log('🛑 Max retries reached, stopping topology auto-refresh');
            this.stopAutoRefresh();
            this.showMaxRetriesTopologyMessage();
        }

        // Cargar datos de ejemplo como fallback
        if (this.nodes.length === 0) {
            console.log('📝 Loading sample data as fallback...');
            this.loadSampleData();
        } else {
            this.hideLoadingState();
        }
    }

    showTopologyUnavailableMessage() {
        this.updateStatus('⚠️', 'Archivo de topología no encontrado - Auto-actualización deshabilitada', 'warning');
        
        if (window.showNotification) {
            window.showNotification('Archivo de topología no encontrado. Auto-actualización deshabilitada.', 'warning', 0);
        }
        
        // Mostrar mensaje en empty state
        this.showEmptyStateWithMessage('📁 Archivo de topología no encontrado', 'Ejecute un escaneo para generar datos de topología');
    }

    showMaxRetriesTopologyMessage() {
        this.updateStatus('❌', 'Máximo de reintentos alcanzado - Auto-actualización deshabilitada', 'error');
        
        if (window.showNotification) {
            window.showNotification('Error cargando topología después de múltiples intentos. Auto-actualización deshabilitada.', 'danger', 0);
        }
        
        this.showEmptyStateWithMessage('🔴 Error de conexión', 'Máximo de reintentos alcanzado');
    }

    showEmptyStateWithMessage(title, subtitle) {
        const emptyElement = document.getElementById('topologyEmpty');
        if (emptyElement) {
            emptyElement.innerHTML = `
                <div class="empty-icon">🌐</div>
                <div class="empty-title">${title}</div>
                <div class="empty-subtitle">${subtitle}</div>
                <button class="btn btn-primary" onclick="window.topologyViewer?.retryTopologyConnection()">
                    🔄 Reintentar Conexión
                </button>
            `;
        }
        this.showEmptyState();
    }

    // Función pública para reintentar conexión manualmente
    retryTopologyConnection() {
        console.log('🔄 Manual topology connection retry requested');
        
        // Reset retry count
        this.retryCount = 0;
        
        // Mostrar loading
        this.showLoadingState();
        this.updateStatus('🔄', 'Reintentando conexión...', 'loading');
        
        // Reintentar carga
        this.loadTopologyData().then(() => {
            // Si es exitoso, reiniciar auto-refresh
            if (!this.autoRefreshInterval) {
                this.startAutoRefresh();
            }
        });
    }

    validateTopologyData(data) {
        try {
            // Verificar estructura básica
            if (!data || typeof data !== 'object') {
                console.warn('⚠️ Topology data is not a valid object');
                return false;
            }

            // Verificar que tenga nodos (puede estar vacío)
            if (!Array.isArray(data.nodes)) {
                console.warn('⚠️ "nodes" field missing or not an array');
                data.nodes = [];
            }

            // Verificar que tenga enlaces (puede estar vacío)
            if (!Array.isArray(data.edges)) {
                console.warn('⚠️ "edges" field missing or not an array');
                data.edges = [];
            }

            // Validar estructura de nodos
            for (let i = 0; i < data.nodes.length; i++) {
                const node = data.nodes[i];
                if (!node.id) {
                    console.warn(`⚠️ Node at index ${i} missing "id" field, assigning auto ID`);
                    node.id = `node_${i}`;
                }
                if (!node.type) {
                    console.warn(`⚠️ Node ${node.id} missing "type" field, assigning "unknown"`);
                    node.type = 'unknown';
                }
                if (!node.label) {
                    node.label = node.id;
                }
            }

            // Validar estructura de enlaces
            for (let i = data.edges.length - 1; i >= 0; i--) {
                const edge = data.edges[i];
                if (!edge.source || !edge.target) {
                    console.warn(`⚠️ Edge at index ${i} missing source/target, removing`);
                    data.edges.splice(i, 1);
                    continue;
                }
                if (!edge.type) {
                    edge.type = 'unknown';
                }
            }

            return true;

        } catch (error) {
            console.error('❌ Error validating topology data:', error);
            return false;
        }
    }

    getNodeTypeStats() {
        return this.nodes.reduce((stats, node) => {
            stats[node.type] = (stats[node.type] || 0) + 1;
            return stats;
        }, {});
    }

    loadSampleData() {
        console.log('📝 Loading sample data for demonstration...');

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
                },
                {
                    id: "192.168.1.10",
                    type: "switch",
                    label: "Switch Principal"
                }
            ],
            edges: [
                {
                    source: "192.168.1.1",
                    target: "192.168.1.10",
                    type: "route"
                },
                {
                    source: "192.168.1.10",
                    target: "192.168.1.100",
                    type: "l2_neighbor"
                },
                {
                    source: "192.168.1.10",
                    target: "192.168.1.101",
                    type: "l2_neighbor"
                },
                {
                    source: "192.168.1.10",
                    target: "192.168.1.102",
                    type: "l2_neighbor"
                }
            ]
        };

        // Procesar datos de ejemplo
        this.processTopologyData(sampleData);
        this.renderNetwork();
        this.updateStats();
        this.updateDeviceList();
        this.hideLoadingState();

        // Actualizar timestamp
        this.lastDataUpdate = new Date();
        this.updateLastUpdateDisplay();

        this.updateStatus('⚠️', 'Mostrando datos de ejemplo - Ejecute un scan para datos reales', 'warning');
    }

    processTopologyData(data) {
        console.log('⚙️ Processing topology data...');
        
        // Procesar nodos
        this.nodes = data.nodes ? data.nodes.map(node => ({
            id: node.id,
            type: node.type || 'host',
            label: node.label || node.id,
            x: Math.random() * this.width,
            y: Math.random() * this.height,
            fx: null, // Fixed position X
            fy: null  // Fixed position Y
        })) : [];

        // Procesar enlaces
        this.links = data.edges ? data.edges.map(edge => ({
            source: edge.source,
            target: edge.target,
            type: edge.type || 'route',
            mac: edge.mac || null
        })) : [];

        // Crear mapa de nodos para referencias rápidas
        this.nodeMap.clear();
        this.nodes.forEach(node => {
            this.nodeMap.set(node.id, node);
        });
        
        console.log(`✅ Processed ${this.nodes.length} nodes, ${this.links.length} links`);
    }

    renderNetwork() {
        if (!this.nodes.length) {
            this.showEmptyState();
            return;
        }

        this.hideEmptyState();

        if (this.currentLayout === 'force') {
            this.renderForceLayout();
        } else {
            this.renderHierarchicalLayout();
        }
        
        console.log(`🎨 Network rendered with ${this.currentLayout} layout`);
    }

    renderForceLayout() {
        // Configurar simulación de fuerzas
        this.simulation = d3.forceSimulation(this.nodes)
            .force('link', d3.forceLink(this.links)
                .id(d => d.id)
                .distance(this.config.simulation.linkDistance)
            )
            .force('charge', d3.forceManyBody()
                .strength(this.config.simulation.chargeStrength)
            )
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide()
                .radius(this.config.simulation.collisionRadius)
            );

        this.renderElements();

        // Configurar tick de la simulación
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
                d.data.node.fx = d.data.node.x; // Fijar posición
                d.data.node.fy = d.data.node.y;
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
                .filter(link => {
                    const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
                    return sourceId === parent.node.id;
                })
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
        this.renderLinks();
        this.renderNodes();
    }

    renderLinks() {
        const linkSelection = this.linkGroup
            .selectAll('.link')
            .data(this.links, d => `${this.getLinkId(d.source)}-${this.getLinkId(d.target)}`);

        linkSelection.exit().remove();

        const linkEnter = linkSelection.enter()
            .append('line')
            .attr('class', d => `link ${d.type}`)
            .attr('stroke-width', this.config.links.widths.default)
            .attr('stroke', d => this.getLinkColor(d.type))
            .attr('marker-end', 'url(#arrowhead)')
            .style('cursor', 'pointer');

        // Merge enter and update selections
        const linkMerged = linkSelection.merge(linkEnter);
        
        // Agregar tooltips y eventos a links
        linkMerged
            .on('mouseover', (event, d) => this.onLinkHover(event, d))
            .on('mouseout', (event, d) => this.onLinkOut(event, d))
            .append('title')
            .text(d => `${d.type.toUpperCase()}: ${this.getLinkId(d.source)} → ${this.getLinkId(d.target)}`);
    }

    renderNodes() {
        const nodeSelection = this.nodeGroup
            .selectAll('.node')
            .data(this.nodes, d => d.id);

        nodeSelection.exit().remove();

        const nodeEnter = nodeSelection.enter()
            .append('g')
            .attr('class', d => `node ${d.type}`)
            .call(this.dragBehavior())
            .style('cursor', 'pointer');

        // Círculo del nodo
        nodeEnter.append('circle')
            .attr('r', d => this.getNodeRadius(d.type))
            .attr('fill', d => this.getNodeColor(d.type))
            .attr('stroke', '#333')
            .attr('stroke-width', 2)
            .style('filter', 'url(#drop-shadow)');

        // Icono del nodo
        nodeEnter.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', '.35em')
            .attr('font-size', '16px')
            .attr('fill', 'white')
            .style('pointer-events', 'none')
            .text(d => this.getNodeIcon(d.type));

        // Etiqueta del nodo
        nodeEnter.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', '30px')
            .attr('font-size', '12px')
            .attr('font-weight', '600')
            .attr('fill', '#2c3e50')
            .style('pointer-events', 'none')
            .text(d => this.truncateLabel(d.label, 15));

        // Merge enter and update selections
        const nodeMerged = nodeSelection.merge(nodeEnter);

        // Eventos y tooltips
        nodeMerged
            .on('click', (event, d) => this.onNodeClick(event, d))
            .on('mouseover', (event, d) => this.onNodeHover(event, d))
            .on('mouseout', (event, d) => this.onNodeOut(event, d));

        // Actualizar tooltips
        nodeMerged.select('title').remove();
        nodeMerged.append('title')
            .text(d => `${d.type.toUpperCase()}: ${d.label}\nID: ${d.id}`);
    }

    dragBehavior() {
        return d3.drag()
            .on('start', (event, d) => {
                if (!event.active && this.simulation) {
                    this.simulation.alphaTarget(this.config.simulation.alphaTarget).restart();
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
                // Mantener posición fija en layout jerárquico
                if (this.currentLayout === 'hierarchical') {
                    d.fx = event.x;
                    d.fy = event.y;
                } else {
                    d.fx = null;
                    d.fy = null;
                }
            });
    }

    // Getters para colores, tamaños e iconos
    getNodeColor(type) {
        return this.config.nodes.colors[type] || this.config.nodes.colors.unknown;
    }

    getNodeRadius(type) {
        return this.config.nodes.sizes[type] || this.config.nodes.sizes.unknown;
    }

    getNodeIcon(type) {
        return this.config.nodes.icons[type] || this.config.nodes.icons.unknown;
    }

    getLinkColor(type) {
        return this.config.links.colors[type] || this.config.links.colors.unknown;
    }

    getLinkId(linkEnd) {
        return typeof linkEnd === 'string' ? linkEnd : linkEnd.id;
    }

    truncateLabel(label, maxLength) {
        if (!label) return '';
        return label.length > maxLength ? label.substring(0, maxLength - 3) + '...' : label;
    }

    // Event handlers
    onNodeClick(event, node) {
        console.log('Node selected:', node);

        // Highlight conexiones
        this.highlightConnections(node.id);

        // Mostrar información detallada
        this.showNodeDetails(node);

        // Notificar click
        if (window.showNotification) {
            window.showNotification(`Nodo seleccionado: ${node.label}`, 'info', 2000);
        }
    }

    onNodeHover(event, node) {
        // Resaltar nodo
        d3.select(event.currentTarget)
            .select('circle')
            .attr('stroke-width', 4)
            .attr('stroke', '#FFD700');
    }

    onNodeOut(event, node) {
        // Quitar resaltado si no está seleccionado
        d3.select(event.currentTarget)
            .select('circle')
            .attr('stroke-width', 2)
            .attr('stroke', '#333');
    }

    onLinkHover(event, link) {
        d3.select(event.currentTarget)
            .attr('stroke-width', this.config.links.widths.highlighted)
            .attr('stroke-opacity', 1);
    }

    onLinkOut(event, link) {
        d3.select(event.currentTarget)
            .attr('stroke-width', this.config.links.widths.default)
            .attr('stroke-opacity', 0.8);
    }

    highlightConnections(nodeId) {
        // Resetear estilos
        this.linkGroup.selectAll('.link')
            .attr('stroke-opacity', 0.3)
            .attr('stroke-width', this.config.links.widths.default);

        this.nodeGroup.selectAll('.node circle')
            .attr('fill-opacity', 0.3);

        // Resaltar conexiones del nodo
        this.linkGroup.selectAll('.link')
            .filter(d => {
                const sourceId = this.getLinkId(d.source);
                const targetId = this.getLinkId(d.target);
                return sourceId === nodeId || targetId === nodeId;
            })
            .attr('stroke-opacity', 1)
            .attr('stroke-width', this.config.links.widths.highlighted);

        // Resaltar nodos conectados
        const connectedNodes = new Set([nodeId]);
        this.links.forEach(link => {
            const sourceId = this.getLinkId(link.source);
            const targetId = this.getLinkId(link.target);

            if (sourceId === nodeId) connectedNodes.add(targetId);
            if (targetId === nodeId) connectedNodes.add(sourceId);
        });

        this.nodeGroup.selectAll('.node circle')
            .filter(d => connectedNodes.has(d.id))
            .attr('fill-opacity', 1);

        // Auto-reset después de 3 segundos
        setTimeout(() => {
            this.resetHighlights();
        }, 3000);
    }

    resetHighlights() {
        this.linkGroup.selectAll('.link')
            .attr('stroke-opacity', 0.8)
            .attr('stroke-width', this.config.links.widths.default);
        this.nodeGroup.selectAll('.node circle')
            .attr('fill-opacity', 1);
    }

    showNodeDetails(node) {
        const connections = this.links.filter(link => {
            const sourceId = this.getLinkId(link.source);
            const targetId = this.getLinkId(link.target);
            return sourceId === node.id || targetId === node.id;
        });

        const details = {
            id: node.id,
            type: node.type,
            label: node.label,
            connections: connections.length,
            connectedTo: connections.map(c => {
                const sourceId = this.getLinkId(c.source);
                const targetId = this.getLinkId(c.target);
                return sourceId === node.id ? targetId : sourceId;
            })
        };

        console.log(`Node details for ${node.label}:`, details);
        
        // Podrías implementar un modal o panel lateral aquí
        // Por ahora solo mostramos en consola
    }

    // Funciones de actualización de UI
    updateStats() {
        const devicesByType = this.nodes.reduce((acc, node) => {
            acc[node.type] = (acc[node.type] || 0) + 1;
            return acc;
        }, {});

        // Actualizar contadores si existen los elementos
        this.updateElementText('deviceCount', this.nodes.length);
        this.updateElementText('connectionCount', this.links.length);
        this.updateElementText('gatewayCount', devicesByType.gateway || 0);
        
        // Actualizar contadores adicionales
        this.updateElementText('totalDevices', this.nodes.length);
        this.updateElementText('totalConnections', this.links.length);
        this.updateElementText('totalGateways', devicesByType.gateway || 0);
    }

    updateDeviceList() {
        const deviceListElement = document.getElementById('deviceList');
        if (!deviceListElement) return;

        if (this.nodes.length === 0) {
            deviceListElement.innerHTML = '<div class="text-muted">No devices detected</div>';
            return;
        }

        // Agrupar por tipo
        const devicesByType = this.nodes.reduce((acc, node) => {
            if (!acc[node.type]) acc[node.type] = [];
            acc[node.type].push(node);
            return acc;
        }, {});

        let html = '';
        Object.entries(devicesByType).forEach(([type, devices]) => {
            html += `
                <div class="device-type-group">
                    <h5 style="color: ${this.getNodeColor(type)}; margin-bottom: 0.5rem;">
                        ${type.toUpperCase()} (${devices.length})
                    </h5>
                    ${devices.map(device => `
                        <div class="device-item" onclick="window.topologyViewer?.focusOnNode('${device.id}')">
                            <span class="device-icon">${this.getNodeIcon(device.type)}</span>
                            <span class="device-name">${device.label}</span>
                        </div>
                    `).join('')}
                </div>
            `;
        });

        deviceListElement.innerHTML = html;
    }

    updateLastUpdateDisplay() {
        if (this.lastDataUpdate) {
            const timestamp = this.lastDataUpdate.toLocaleString('es-ES', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            
            this.updateElementText('lastUpdate', timestamp);
            this.updateElementText('topologyLastUpdate', timestamp);
        }
    }

    updateElementText(elementId, text) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text;
        }
    }

    // Funciones de control de la topología
    focusOnNode(nodeId) {
        const node = this.nodes.find(n => n.id === nodeId);
        if (!node || !this.zoomBehavior) return;

        // Centrar vista en el nodo
        const transform = d3.zoomIdentity
            .translate(this.width / 2 - node.x, this.height / 2 - node.y)
            .scale(1.5);

        this.svg.transition()
            .duration(750)
            .call(this.zoomBehavior.transform, transform);

        // Simular click en el nodo después de la transición
        setTimeout(() => {
            this.highlightConnections(nodeId);
        }, 750);

        console.log(`🎯 Focused on node: ${node.label}`);
    }

    toggleLayout() {
        this.currentLayout = this.currentLayout === 'force' ? 'hierarchical' : 'force';

        // Parar simulación actual si existe
        if (this.simulation) {
            this.simulation.stop();
        }

        // Reset fixed positions for force layout
        if (this.currentLayout === 'force') {
            this.nodes.forEach(node => {
                node.fx = null;
                node.fy = null;
            });
        }

        this.renderNetwork();
        
        console.log(`📊 Layout changed to: ${this.currentLayout}`);
        
        if (window.showNotification) {
            window.showNotification(`Layout cambiado a: ${this.currentLayout}`, 'info', 2000);
        }
    }

    centerView() {
        if (!this.zoomBehavior) return;
        
        // Centrar vista en el origen
        const transform = d3.zoomIdentity
            .translate(this.width / 2, this.height / 2)
            .scale(1);

        this.svg.transition()
            .duration(750)
            .call(this.zoomBehavior.transform, transform);
            
        console.log('🎯 View centered');
    }

    resetZoom() {
        if (!this.zoomBehavior) return;
        
        // Reset zoom a escala 1
        const transform = d3.zoomIdentity;

        this.svg.transition()
            .duration(750)
            .call(this.zoomBehavior.transform, transform);
            
        console.log('🔍 Zoom reset');
    }

    // Estados de la UI
    showLoadingState() {
        const loadingElement = document.getElementById('topologyLoading');
        const emptyElement = document.getElementById('topologyEmpty');
        
        if (loadingElement) {
            loadingElement.classList.remove('d-none');
        }
        if (emptyElement) {
            emptyElement.classList.add('d-none');
        }
    }

    hideLoadingState() {
        const loadingElement = document.getElementById('topologyLoading');
        if (loadingElement) {
            loadingElement.classList.add('d-none');
        }
    }

    showEmptyState() {
        const loadingElement = document.getElementById('topologyLoading');
        const emptyElement = document.getElementById('topologyEmpty');
        
        if (loadingElement) {
            loadingElement.classList.add('d-none');
        }
        if (emptyElement) {
            emptyElement.classList.remove('d-none');
        }
    }

    hideEmptyState() {
        const emptyElement = document.getElementById('topologyEmpty');
        if (emptyElement) {
            emptyElement.classList.add('d-none');
        }
    }

    showError(message) {
        console.error('Topology error:', message);
        
        if (window.showNotification) {
            window.showNotification(message, 'danger');
        }
        
        this.hideLoadingState();
        
        // Mostrar mensaje de error en el canvas si está vacío
        if (this.nodes.length === 0) {
            this.showEmptyState();
        }
    }

    updateStatus(indicator, message, type) {
        // Intentar actualizar el status si existe el elemento
        const statusElement = document.getElementById('status');
        if (statusElement) {
            const indicatorElement = statusElement.querySelector('.status-indicator');
            const messageElement = statusElement.querySelector('span:last-child');

            if (indicatorElement) indicatorElement.textContent = indicator;
            if (messageElement) messageElement.textContent = message;

            statusElement.className = `status ${type}`;
        }
        
        // Log del status
        console.log(`Status: ${indicator} ${message}`);
    }

    // Auto-refresh
    startAutoRefresh() {
        // Limpiar interval existente
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        
        // Configurar nuevo interval
        this.autoRefreshInterval = setInterval(() => {
            console.log('🔄 Auto-refreshing topology...');
            this.loadTopologyData();
        }, TopologyApp?.config?.refreshInterval || 5 * 60 * 1000);
        
        console.log('⏰ Auto-refresh started');
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
            console.log('⏰ Auto-refresh stopped');
        }
    }

    // Responsive handling
    handleResize() {
        const container = this.svg.node().parentElement;
        if (container) {
            const rect = container.getBoundingClientRect();
            const newWidth = rect.width || 800;
            const newHeight = rect.height || 600;
            
            if (newWidth !== this.width || newHeight !== this.height) {
                this.width = newWidth;
                this.height = newHeight;
                
                this.svg
                    .attr('width', this.width)
                    .attr('height', this.height)
                    .attr('viewBox', `0 0 ${this.width} ${this.height}`);
                
                // Reposicionar center force si existe simulación
                if (this.simulation) {
                    this.simulation.force('center', d3.forceCenter(this.width / 2, this.height / 2));
                    this.simulation.alpha(0.3).restart();
                }
                
                console.log(`📐 Topology resized to: ${this.width}x${this.height}`);
            }
        }
    }

    // Cleanup
    destroy() {
        console.log('🧹 Destroying NetworkTopologyViewer...');
        
        // Parar auto-refresh
        this.stopAutoRefresh();
        
        // Parar simulación
        if (this.simulation) {
            this.simulation.stop();
        }
        
        // Limpiar SVG
        if (this.svg) {
            this.svg.selectAll('*').remove();
        }
        
        // Limpiar referencias
        this.nodes = [];
        this.links = [];
        this.nodeMap.clear();
        this.simulation = null;
        this.svg = null;
        
        console.log('✅ NetworkTopologyViewer destroyed');
    }

    // Métodos públicos para compatibilidad
    refreshTopology() {
        return this.loadTopologyData();
    }

    getNodes() {
        return this.nodes;
    }

    getLinks() {
        return this.links;
    }

    getStats() {
        const devicesByType = this.nodes.reduce((acc, node) => {
            acc[node.type] = (acc[node.type] || 0) + 1;
            return acc;
        }, {});

        return {
            totalNodes: this.nodes.length,
            totalLinks: this.links.length,
            nodesByType: devicesByType,
            lastUpdate: this.lastDataUpdate,
            currentLayout: this.currentLayout
        };
    }
}

// ================================
// FUNCIONES GLOBALES PARA COMPATIBILIDAD
// ================================

// Funciones globales para la interfaz (compatibilidad con HTML existente)
window.refreshTopology = function() {
    if (window.topologyViewer && window.topologyViewer.loadTopologyData) {
        window.topologyViewer.loadTopologyData();
    } else {
        console.warn('⚠️ Topology viewer not initialized');
    }
};

window.toggleLayout = function() {
    if (window.topologyViewer && window.topologyViewer.toggleLayout) {
        window.topologyViewer.toggleLayout();
    } else {
        console.warn('⚠️ Topology viewer not initialized');
    }
};

window.centerView = function() {
    if (window.topologyViewer && window.topologyViewer.centerView) {
        window.topologyViewer.centerView();
    } else {
        console.warn('⚠️ Topology viewer not initialized');
    }
};

window.resetZoom = function() {
    if (window.topologyViewer && window.topologyViewer.resetZoom) {
        window.topologyViewer.resetZoom();
    } else {
        console.warn('⚠️ Topology viewer not initialized');
    }
};

// ================================
// AUTO-INICIALIZACIÓN Y EVENTOS
// ================================

// Event listener para resize
window.addEventListener('resize', debounce(() => {
    if (window.topologyViewer && window.topologyViewer.handleResize) {
        window.topologyViewer.handleResize();
    }
}, 250));

// Event listener para visibilidad de página
document.addEventListener('visibilitychange', () => {
    if (window.topologyViewer) {
        if (document.hidden) {
            console.log('📱 Page hidden, stopping auto-refresh');
            window.topologyViewer.stopAutoRefresh();
        } else {
            console.log('📱 Page visible, starting auto-refresh');
            window.topologyViewer.startAutoRefresh();
            // Refresh inmediato al volver a la página
            setTimeout(() => {
                window.topologyViewer.loadTopologyData();
            }, 1000);
        }
    }
});

// Cleanup al salir
window.addEventListener('beforeunload', () => {
    if (window.topologyViewer && window.topologyViewer.destroy) {
        window.topologyViewer.destroy();
    }
});

// Función de utilidad para debounce (si no está disponible globalmente)
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Exportar la clase para uso módulo
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NetworkTopologyViewer;
}

// Exportar globalmente
window.NetworkTopologyViewer = NetworkTopologyViewer;

console.log('🌐 NetworkTopologyViewer class loaded and ready');