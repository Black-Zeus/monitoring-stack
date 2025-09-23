/**
 * topology-viewer/static/js/dashboard.js
 * Lógica específica del dashboard principal
 * Maneja overview cards, quick actions, integración de topología y estado del sistema
 */

class DashboardManager {
    constructor() {
        this.isInitialized = false;
        this.refreshIntervals = {
            systemStatus: null,
            topologyUpdate: null
        };
        
        // Configuración del dashboard
        this.config = {
            refreshIntervals: {
                systemStatus: 30 * 1000,      // 30 segundos
                topologyData: 5 * 60 * 1000,  // 5 minutos
                notifications: 10 * 1000      // 10 segundos
            },
            maxRetries: 3,
            retryDelay: 5000
        };
        
        // Estado del dashboard
        this.state = {
            systemData: null,
            healthData: null,
            lastUpdate: null,
            retryCount: 0,
            isRefreshing: false
        };
        
        console.log('📊 DashboardManager created');
    }

    async initialize() {
        if (this.isInitialized) {
            console.warn('⚠️ Dashboard already initialized');
            return;
        }

        try {
            console.log('🚀 Initializing Dashboard...');
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Cargar datos iniciales
            await this.loadInitialData();
            
            // Inicializar topology viewer si está disponible
            this.initializeTopologyViewer();
            
            // Configurar auto-refresh
            this.startAutoRefresh();
            
            this.isInitialized = true;
            console.log('✅ Dashboard initialized successfully');
            
            // Notificar inicialización exitosa
            this.addSystemNotification('Dashboard inicializado correctamente', 'success');
            
        } catch (error) {
            console.error('❌ Error initializing dashboard:', error);
            this.addSystemNotification('Error inicializando dashboard', 'danger');
        }
    }

    setupEventListeners() {
        console.log('🎯 Setting up dashboard event listeners...');
        
        // Quick Actions
        const quickScanBtn = document.getElementById('quickScanBtn');
        if (quickScanBtn) {
            quickScanBtn.addEventListener('click', () => this.handleQuickScan());
        }
        
        const refreshTopologyBtn = document.getElementById('refreshTopologyBtn');
        if (refreshTopologyBtn) {
            refreshTopologyBtn.addEventListener('click', () => this.handleRefreshTopology());
        }
        
        // Topology Controls
        const topologyRefreshBtn = document.getElementById('topologyRefreshBtn');
        if (topologyRefreshBtn) {
            topologyRefreshBtn.addEventListener('click', () => this.handleRefreshTopology());
        }
        
        const toggleLayoutBtn = document.getElementById('toggleLayoutBtn');
        if (toggleLayoutBtn) {
            toggleLayoutBtn.addEventListener('click', () => this.handleToggleLayout());
        }
        
        const centerViewBtn = document.getElementById('centerViewBtn');
        if (centerViewBtn) {
            centerViewBtn.addEventListener('click', () => this.handleCenterView());
        }
        
        const resetZoomBtn = document.getElementById('resetZoomBtn');
        if (resetZoomBtn) {
            resetZoomBtn.addEventListener('click', () => this.handleResetZoom());
        }
        
        // Empty state scan button
        const emptyStateScanBtn = document.getElementById('emptyStateScanBtn');
        if (emptyStateScanBtn) {
            emptyStateScanBtn.addEventListener('click', () => this.handleQuickScan());
        }
        
        console.log('✅ Event listeners configured');
    }

    async loadInitialData() {
        console.log('📥 Loading initial dashboard data...');
        
        try {
            // Cargar datos en paralelo
            const [systemData, healthData] = await Promise.all([
                this.loadSystemStatus(),
                this.loadHealthStatus()
            ]);
            
            // Actualizar UI con datos cargados
            this.updateSystemStatusCard(systemData);
            this.updateHealthIndicators(healthData);
            
            console.log('✅ Initial data loaded successfully');
            
        } catch (error) {
            console.error('❌ Error loading initial data:', error);
            this.handleDataLoadError(error);
        }
    }

    async loadSystemStatus() {
        try {
            console.log('📊 Loading system status...');
            
            const data = await window.apiClient.get('/status');
            this.state.systemData = data;
            this.state.lastUpdate = new Date();
            
            console.log('✅ System status loaded:', data);
            return data;
            
        } catch (error) {
            console.error('❌ Error loading system status:', error);
            throw error;
        }
    }

    async loadHealthStatus() {
        try {
            console.log('🏥 Loading health status...');
            
            const data = await window.apiClient.get('/health');
            this.state.healthData = data;
            
            console.log('✅ Health status loaded:', data);
            return data;
            
        } catch (error) {
            console.error('❌ Error loading health status:', error);
            throw error;
        }
    }

    updateSystemStatusCard(data) {
        if (!data) return;
        
        console.log('🔄 Updating system status card...');
        
        const statusIndicator = document.getElementById('systemStatusIndicator');
        if (statusIndicator) {
            const isHealthy = data.server_status === 'running';
            const statusClass = isHealthy ? 'alert-success' : 'alert-warning';
            const statusIcon = isHealthy ? '✅' : '⚠️';
            
            statusIndicator.className = `alert ${statusClass}`;
            statusIndicator.innerHTML = `
                <span>${statusIcon}</span>
                <div>
                    <strong>Server:</strong> ${data.server_status || 'Unknown'}<br>
                    <strong>Scans:</strong> ${data.last_scan_count || 0} básicos, ${data.advanced_scan_count || 0} avanzados<br>
                    <strong>Networks:</strong> ${data.configuration?.total_networks || 0} configuradas
                </div>
            `;
        }
        
        // Actualizar métricas de red
        this.updateNetworkStats(data);
        
        // Actualizar información de última actualización
        this.updateLastUpdateInfo(data);
        
        console.log('✅ System status card updated');
    }

    updateNetworkStats(data) {
        // Actualizar contadores principales
        const totalDevices = document.getElementById('totalDevices');
        const totalConnections = document.getElementById('totalConnections');
        const totalGateways = document.getElementById('totalGateways');
        
        if (totalDevices) {
            totalDevices.textContent = data.last_scan_count || 0;
        }
        
        if (totalConnections) {
            totalConnections.textContent = data.advanced_scan_count || 0;
        }
        
        if (totalGateways) {
            totalGateways.textContent = data.configuration?.enabled_networks || 0;
        }
    }

    updateLastUpdateInfo(data) {
        const lastUpdateElement = document.getElementById('lastUpdateInfo');
        if (!lastUpdateElement) return;
        
        if (data.last_scan_time || data.last_advanced_scan_time) {
            const lastScan = data.last_scan_time || data.last_advanced_scan_time;
            const updateTime = window.TopologyApp?.utils?.formatDateTime(lastScan) || 
                             new Date(lastScan).toLocaleString();
            
            lastUpdateElement.innerHTML = `
                <div><strong>Último escaneo:</strong> ${updateTime}</div>
                <div><strong>Red objetivo:</strong> ${data.target_network || 'No configurada'}</div>
                <div><strong>Topología:</strong> ${data.topology_available ? 'Disponible' : 'No disponible'}</div>
            `;
        } else {
            lastUpdateElement.innerHTML = `
                <div class="text-muted">
                    <div>📋 No hay datos de escaneo disponibles</div>
                    <div>Ejecute un escaneo para ver información</div>
                </div>
            `;
        }
    }

    updateHealthIndicators(data) {
        if (!data) return;
        
        console.log('🔄 Updating health indicators...');
        
        // Actualizar indicadores adicionales basados en health data
        // Por ejemplo, podrías actualizar algún indicador de conectividad
        
        console.log('✅ Health indicators updated');
    }

    initializeTopologyViewer() {
        console.log('🌐 Initializing topology viewer...');
        
        try {
            // Solo inicializar si estamos en la página del dashboard y existe el contenedor
            const topologySvg = document.getElementById('topology-svg');
            if (topologySvg && window.NetworkTopologyViewer) {
                window.topologyViewer = new NetworkTopologyViewer('topology-svg');
                console.log('✅ Topology viewer initialized');
                
                // Configurar callback para updates
                this.setupTopologyCallbacks();
            } else {
                console.log('ℹ️ Topology viewer not available on this page');
            }
        } catch (error) {
            console.error('❌ Error initializing topology viewer:', error);
            this.addSystemNotification('Error inicializando visualizador de topología', 'warning');
        }
    }

    setupTopologyCallbacks() {
        // Si el topology viewer tiene eventos, configurarlos aquí
        if (window.topologyViewer) {
            // Por ejemplo, escuchar cuando se actualicen los datos de topología
            // window.topologyViewer.on('dataUpdated', (stats) => {
            //     this.updateTopologyStats(stats);
            // });
        }
    }

    // ================================
    // QUICK ACTIONS HANDLERS
    // ================================

    async handleQuickScan() {
        console.log('⚡ Executing quick scan...');
        
        const quickScanBtn = document.getElementById('quickScanBtn');
        const emptyStateScanBtn = document.getElementById('emptyStateScanBtn');
        
        // Deshabilitar botones durante el scan
        if (quickScanBtn) {
            quickScanBtn.disabled = true;
            quickScanBtn.innerHTML = '🔄 Escaneando...';
        }
        if (emptyStateScanBtn) {
            emptyStateScanBtn.disabled = true;
            emptyStateScanBtn.innerHTML = '🔄 Escaneando...';
        }
        
        try {
            this.addSystemNotification('Iniciando escaneo rápido...', 'info');
            
            const response = await window.apiClient.post('/scan', {
                network: '192.168.1.0/24'
            });
            
            console.log('✅ Quick scan started:', response);
            this.addSystemNotification(`Escaneo iniciado: ${response.message || 'Proceso comenzado'}`, 'success');
            
            // Programar actualización de datos después del scan
            setTimeout(() => {
                this.loadSystemStatus().then(data => {
                    this.updateSystemStatusCard(data);
                });
            }, 5000); // 5 segundos después
            
            // Refresh topology también
            setTimeout(() => {
                this.handleRefreshTopology();
            }, 10000); // 10 segundos después
            
        } catch (error) {
            console.error('❌ Quick scan error:', error);
            const errorMessage = window.TopologyApp?.utils?.handleApiError(error, 'Quick Scan') || error.message;
            this.addSystemNotification(`Error en escaneo: ${errorMessage}`, 'danger');
        } finally {
            // Rehabilitar botones
            if (quickScanBtn) {
                quickScanBtn.disabled = false;
                quickScanBtn.innerHTML = '⚡ Quick Scan';
            }
            if (emptyStateScanBtn) {
                emptyStateScanBtn.disabled = false;
                emptyStateScanBtn.innerHTML = '🚀 Start Quick Scan';
            }
        }
    }

    handleRefreshTopology() {
        console.log('🔄 Refreshing topology...');
        
        if (window.topologyViewer && window.topologyViewer.loadTopologyData) {
            window.topologyViewer.loadTopologyData();
            this.addSystemNotification('Actualizando topología...', 'info', 2000);
        } else {
            console.warn('⚠️ Topology viewer not available');
            this.addSystemNotification('Visualizador de topología no disponible', 'warning');
        }
    }

    handleToggleLayout() {
        console.log('📊 Toggling layout...');
        
        if (window.topologyViewer && window.topologyViewer.toggleLayout) {
            window.topologyViewer.toggleLayout();
            this.addSystemNotification('Layout de topología cambiado', 'info', 2000);
        } else {
            console.warn('⚠️ Topology viewer not available');
            this.addSystemNotification('Visualizador de topología no disponible', 'warning');
        }
    }

    handleCenterView() {
        console.log('🎯 Centering view...');
        
        if (window.topologyViewer && window.topologyViewer.centerView) {
            window.topologyViewer.centerView();
            this.addSystemNotification('Vista centrada', 'info', 1500);
        } else {
            console.warn('⚠️ Topology viewer not available');
        }
    }

    handleResetZoom() {
        console.log('🔍 Resetting zoom...');
        
        if (window.topologyViewer && window.topologyViewer.resetZoom) {
            window.topologyViewer.resetZoom();
            this.addSystemNotification('Zoom restablecido', 'info', 1500);
        } else {
            console.warn('⚠️ Topology viewer not available');
        }
    }

    // ================================
    // AUTO-REFRESH SYSTEM
    // ================================

    startAutoRefresh() {
        console.log('⏰ Starting auto-refresh system...');
        
        // System status refresh
        this.refreshIntervals.systemStatus = setInterval(async () => {
            if (!this.state.isRefreshing) {
                try {
                    this.state.isRefreshing = true;
                    const data = await this.loadSystemStatus();
                    this.updateSystemStatusCard(data);
                    
                    // Reset retry count on successful refresh
                    this.state.retryCount = 0;
                    
                } catch (error) {
                    console.error('❌ Auto-refresh error:', error);
                    
                    // Si es un error 404, detener auto-refresh y mostrar mensaje
                    if (error.message.includes('404')) {
                        console.log('🛑 Stopping auto-refresh due to 404 errors');
                        this.stopAutoRefresh();
                        this.showServiceUnavailableMessage();
                        return;
                    }
                    
                    // Para otros errores, incrementar retry count
                    this.state.retryCount++;
                    if (this.state.retryCount >= this.config.maxRetries) {
                        console.log('🛑 Max retries reached, stopping auto-refresh');
                        this.stopAutoRefresh();
                        this.showMaxRetriesMessage();
                    }
                } finally {
                    this.state.isRefreshing = false;
                }
            }
        }, this.config.refreshIntervals.systemStatus);
        
        console.log('✅ Auto-refresh system started');
    }

    stopAutoRefresh() {
        console.log('⏰ Stopping auto-refresh system...');
        
        Object.values(this.refreshIntervals).forEach(interval => {
            if (interval) {
                clearInterval(interval);
            }
        });
        
        // Reset intervals
        this.refreshIntervals = {
            systemStatus: null,
            topologyUpdate: null
        };
        
        console.log('✅ Auto-refresh system stopped');
    }

    showServiceUnavailableMessage() {
        console.log('📢 Showing service unavailable message');
        
        const statusIndicator = document.getElementById('systemStatusIndicator');
        if (statusIndicator) {
            statusIndicator.className = 'alert alert-warning';
            statusIndicator.innerHTML = `
                <span>⚠️</span>
                <div>
                    <strong>Servicios no disponibles</strong><br>
                    Los endpoints del servidor no están respondiendo<br>
                    <small>Auto-actualización deshabilitada. <button class="btn btn-sm btn-primary" onclick="window.dashboardManager?.retryConnection()" style="margin-top: 5px;">🔄 Reintentar</button></small>
                </div>
            `;
        }
        
        this.addSystemNotification('Servicios del servidor no disponibles - Auto-actualización deshabilitada', 'warning', 0);
    }

    showMaxRetriesMessage() {
        console.log('📢 Showing max retries message');
        
        const statusIndicator = document.getElementById('systemStatusIndicator');
        if (statusIndicator) {
            statusIndicator.className = 'alert alert-danger';
            statusIndicator.innerHTML = `
                <span>❌</span>
                <div>
                    <strong>Conexión fallida</strong><br>
                    Máximo de reintentos alcanzado<br>
                    <small>Auto-actualización deshabilitada. <button class="btn btn-sm btn-primary" onclick="window.dashboardManager?.retryConnection()" style="margin-top: 5px;">🔄 Reintentar</button></small>
                </div>
            `;
        }
        
        this.addSystemNotification('Conexión fallida después de múltiples intentos - Auto-actualización deshabilitada', 'danger', 0);
    }

    // ================================
    // SYSTEM NOTIFICATIONS
    // ================================

    addSystemNotification(message, type = 'info', duration = 5000) {
        const notificationsContainer = document.getElementById('systemNotifications');
        if (!notificationsContainer) {
            console.warn('⚠️ Notifications container not found');
            return;
        }
        
        const notification = this.createNotificationElement(message, type, duration);
        
        // Insertar al principio
        notificationsContainer.insertBefore(notification, notificationsContainer.firstChild);
        
        // Mantener solo las últimas 5 notificaciones
        while (notificationsContainer.children.length > 5) {
            notificationsContainer.removeChild(notificationsContainer.lastChild);
        }
        
        // Auto-remove si tiene duración
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, duration);
        }
        
        console.log(`📢 System notification: [${type.toUpperCase()}] ${message}`);
    }

    createNotificationElement(message, type, duration) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type}`;
        
        const icon = this.getNotificationIcon(type);
        const timestamp = new Date().toLocaleTimeString('es-ES', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        notification.innerHTML = `
            <span>${icon}</span>
            <span class="notification-message">${message}</span>
            <small class="notification-time text-muted" style="margin-left: auto; font-size: 0.8rem;">${timestamp}</small>
        `;
        
        // Animación de entrada
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(20px)';
        
        requestAnimationFrame(() => {
            notification.style.transition = 'all 0.3s ease';
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        });
        
        return notification;
    }

    getNotificationIcon(type) {
        const icons = {
            'success': '✅',
            'warning': '⚠️',
            'danger': '❌',
            'error': '❌',
            'info': 'ℹ️',
            'loading': '🔄'
        };
        return icons[type] || 'ℹ️';
    }

    // ================================
    // ERROR HANDLING
    // ================================

    handleDataLoadError(error) {
        console.error('❌ Data load error:', error);
        
        const errorMessage = this.getErrorMessage(error);
        
        // Si es error 404, detener inmediatamente todo el sistema de retry
        if (error.message.includes('404')) {
            console.log('🛑 404 error detected, stopping all retry attempts and auto-refresh');
            this.stopAutoRefresh();
            this.showServiceUnavailableMessage();
            return; // Salir sin programar más reintentos
        }
        
        // Mostrar error en system status card
        const statusIndicator = document.getElementById('systemStatusIndicator');
        if (statusIndicator) {
            statusIndicator.className = 'alert alert-danger';
            statusIndicator.innerHTML = `
                <span>❌</span>
                <div>
                    <strong>Error de conexión</strong><br>
                    ${errorMessage}<br>
                    <small>Reintentando automáticamente...</small>
                </div>
            `;
        }
        
        this.addSystemNotification(`Error cargando datos: ${errorMessage}`, 'danger');
        
        // Solo hacer retry para errores que NO sean 404
        this.scheduleRetry();
    }

    getErrorMessage(error) {
        if (error.message.includes('timeout')) {
            return 'Timeout - La operación tardó demasiado';
        } else if (error.message.includes('fetch')) {
            return 'Error de conexión - Verifique la red';
        } else if (error.message.includes('404')) {
            return 'Servicio no encontrado';
        } else if (error.message.includes('500')) {
            return 'Error del servidor';
        } else {
            return error.message || 'Error desconocido';
        }
    }

    scheduleRetry() {
        if (this.state.retryCount >= this.config.maxRetries) {
            console.log('❌ Max retries reached, stopping retry attempts and auto-refresh');
            this.stopAutoRefresh();
            this.showMaxRetriesMessage();
            return;
        }
        
        this.state.retryCount++;
        const delay = this.config.retryDelay * this.state.retryCount;
        
        console.log(`🔄 Scheduling retry ${this.state.retryCount}/${this.config.maxRetries} in ${delay}ms`);
        
        setTimeout(async () => {
            try {
                await this.loadInitialData();
                this.state.retryCount = 0; // Reset on success
                this.addSystemNotification('Conexión restablecida', 'success');
                
                // Reiniciar auto-refresh si se había detenido
                if (!this.refreshIntervals.systemStatus) {
                    this.startAutoRefresh();
                }
            } catch (error) {
                // Si es 404, detener todo
                if (error.message.includes('404')) {
                    console.log('🛑 404 error detected, stopping all retry attempts');
                    this.stopAutoRefresh();
                    this.showServiceUnavailableMessage();
                    return;
                }
                
                this.handleDataLoadError(error);
            }
        }, delay);
    }

    // Función pública para reintentar conexión manualmente
    async retryConnection() {
        console.log('🔄 Manual connection retry requested');
        
        // Reset retry count
        this.state.retryCount = 0;
        
        // Mostrar estado de reintento
        const statusIndicator = document.getElementById('systemStatusIndicator');
        if (statusIndicator) {
            statusIndicator.className = 'alert alert-info';
            statusIndicator.innerHTML = `
                <span>🔄</span>
                <div>
                    <strong>Reintentando conexión...</strong><br>
                    Verificando disponibilidad de servicios<br>
                    <div class="loading-spinner" style="margin-top: 5px;"></div>
                </div>
            `;
        }
        
        this.addSystemNotification('Reintentando conexión al servidor...', 'info');
        
        try {
            await this.loadInitialData();
            
            // Si es exitoso, reiniciar auto-refresh
            if (!this.refreshIntervals.systemStatus) {
                this.startAutoRefresh();
            }
            
            this.addSystemNotification('Conexión restablecida exitosamente', 'success');
            
        } catch (error) {
            console.error('❌ Manual retry failed:', error);
            
            if (error.message.includes('404')) {
                this.showServiceUnavailableMessage();
            } else {
                this.handleDataLoadError(error);
            }
        }
    }

    // ================================
    // PUBLIC API
    // ================================

    getState() {
        return {
            ...this.state,
            isInitialized: this.isInitialized,
            config: this.config
        };
    }

    async refreshDashboard() {
        console.log('🔄 Manual dashboard refresh requested');
        
        try {
            await this.loadInitialData();
            this.addSystemNotification('Dashboard actualizado', 'success');
            
            // También refresh topology si está disponible
            if (window.topologyViewer) {
                this.handleRefreshTopology();
            }
        } catch (error) {
            this.handleDataLoadError(error);
        }
    }

    // ================================
    // CLEANUP
    // ================================

    destroy() {
        console.log('🧹 Destroying DashboardManager...');
        
        this.stopAutoRefresh();
        
        // Clear state
        this.state = {
            systemData: null,
            healthData: null,
            lastUpdate: null,
            retryCount: 0,
            isRefreshing: false
        };
        
        this.isInitialized = false;
        
        console.log('✅ DashboardManager destroyed');
    }
}

// ================================
// INICIALIZACIÓN AUTOMÁTICA
// ================================

// Variable global para el dashboard manager
window.dashboardManager = null;

// Auto-inicialización cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', async function() {
    // Solo inicializar si estamos en la página del dashboard
    if (window.TopologyApp?.state?.currentPage === 'index' || 
        window.location.pathname.endsWith('index.html') || 
        window.location.pathname === '/' ||
        window.location.pathname.endsWith('/')) {
        
        console.log('📊 Dashboard page detected, initializing DashboardManager...');
        
        try {
            // Crear instancia del dashboard manager
            window.dashboardManager = new DashboardManager();
            
            // Inicializar
            await window.dashboardManager.initialize();
            
            console.log('✅ Dashboard page initialization complete');
            
        } catch (error) {
            console.error('❌ Error initializing dashboard page:', error);
        }
    } else {
        console.log('ℹ️ Not a dashboard page, skipping DashboardManager initialization');
    }
});

// Cleanup al salir de la página
window.addEventListener('beforeunload', () => {
    if (window.dashboardManager) {
        window.dashboardManager.destroy();
    }
});

// Event listener para cambios de visibilidad
document.addEventListener('visibilitychange', () => {
    if (window.dashboardManager) {
        if (document.hidden) {
            console.log('📱 Dashboard page hidden, stopping auto-refresh');
            window.dashboardManager.stopAutoRefresh();
        } else {
            console.log('📱 Dashboard page visible, starting auto-refresh');
            window.dashboardManager.startAutoRefresh();
            // Refresh inmediato
            setTimeout(() => {
                window.dashboardManager.refreshDashboard();
            }, 1000);
        }
    }
});

// Funciones globales para compatibilidad con HTML inline
window.quickScan = function() {
    if (window.dashboardManager) {
        window.dashboardManager.handleQuickScan();
    } else {
        console.warn('⚠️ Dashboard manager not initialized');
    }
};

window.refreshDashboard = function() {
    if (window.dashboardManager) {
        window.dashboardManager.refreshDashboard();
    } else {
        console.warn('⚠️ Dashboard manager not initialized');
    }
};

console.log('📊 Dashboard module loaded and ready');

// Export para uso como módulo
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DashboardManager;
}