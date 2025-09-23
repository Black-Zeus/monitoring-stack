/**
 * topology-viewer/static/js/script.js
 * Scripts generales para toda la aplicación
 * Funciones compartidas, navegación, utilidades y configuración global
 */

// ================================
// CONFIGURACIÓN GLOBAL
// ================================
window.TopologyApp = {
    config: {
        apiBaseUrl: '',
        refreshInterval: 5 * 60 * 1000, // 5 minutos
        requestTimeout: 10000, // 10 segundos
        maxNotifications: 5,
        debounceDelay: 300
    },
    
    state: {
        currentPage: '',
        isLoading: false,
        notifications: [],
        lastUpdate: null,
        systemStatus: null
    },
    
    intervals: {
        autoRefresh: null,
        statusCheck: null
    }
};

// ================================
// INICIALIZACIÓN
// ================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🌐 Topology Viewer - Global scripts loaded');
    
    // Detectar página actual
    detectCurrentPage();
    
    // Configurar navegación
    setupNavigation();
    
    // Configurar manejo global de errores
    setupErrorHandling();
    
    // Inicializar utilidades
    initializeUtils();
    
    console.log('✅ Global initialization complete');
});

// ================================
// NAVEGACIÓN Y PÁGINA ACTUAL
// ================================
function detectCurrentPage() {
    const path = window.location.pathname;
    const filename = path.split('/').pop() || 'index.html';
    
    TopologyApp.state.currentPage = filename.replace('.html', '');
    
    console.log(`📄 Current page: ${TopologyApp.state.currentPage}`);
    
    // Marcar enlace activo en navegación
    setActiveNav(filename);
}

function setActiveNav(currentFile) {
    // Remover clases activas existentes
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // Buscar y activar enlace correspondiente
    const activeLink = document.querySelector(`.nav-link[href="${currentFile}"]`);
    if (activeLink) {
        activeLink.classList.add('active');
        console.log(`🎯 Active nav set: ${currentFile}`);
    }
}

function setupNavigation() {
    // Agregar listeners a enlaces de navegación
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            // Si es una página local, mostrar efecto de loading
            if (href && !href.startsWith('http') && href.endsWith('.html')) {
                showPageTransition();
            }
        });
    });
    
    console.log('🧭 Navigation setup complete');
}

function showPageTransition() {
    // Efecto visual de transición entre páginas
    const body = document.body;
    body.style.opacity = '0.7';
    body.style.transition = 'opacity 0.3s ease';
    
    setTimeout(() => {
        body.style.opacity = '1';
    }, 300);
}

// ================================
// UTILIDADES HTTP
// ================================
class ApiClient {
    constructor(baseUrl = '', timeout = 10000) {
        this.baseUrl = baseUrl;
        this.timeout = timeout;
    }
    
    async request(endpoint, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            },
            signal: controller.signal
        };
        
        const config = { ...defaultOptions, ...options };
        
        try {
            console.log(`🔄 API Request: ${config.method} ${endpoint}`);
            
            const response = await fetch(this.baseUrl + endpoint, config);
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Verificar content type
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                console.log(`✅ API Response: ${endpoint}`, data);
                return data;
            } else {
                const text = await response.text();
                console.log(`✅ API Response (text): ${endpoint}`);
                return text;
            }
            
        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            
            console.error(`❌ API Error: ${endpoint}`, error);
            throw error;
        }
    }
    
    async get(endpoint, params = {}) {
        const url = new URL(endpoint, window.location.origin);
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                url.searchParams.append(key, value);
            }
        });
        
        return this.request(url.pathname + url.search);
    }
    
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }
    
    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }
}

// Instancia global del cliente API
window.apiClient = new ApiClient();

// ================================
// SISTEMA DE NOTIFICACIONES
// ================================
class NotificationSystem {
    constructor(containerId = 'systemNotifications') {
        this.container = document.getElementById(containerId);
        this.notifications = [];
        this.maxNotifications = TopologyApp.config.maxNotifications;
    }
    
    show(message, type = 'info', duration = 5000) {
        const notification = this.createNotification(message, type, duration);
        this.addNotification(notification);
        
        console.log(`📢 Notification: [${type.toUpperCase()}] ${message}`);
        
        return notification;
    }
    
    createNotification(message, type, duration) {
        const id = 'notification_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        const notification = {
            id,
            message,
            type,
            timestamp: new Date(),
            duration,
            element: null
        };
        
        // Crear elemento DOM
        const element = document.createElement('div');
        element.id = id;
        element.className = `alert alert-${type}`;
        element.innerHTML = `
            <span>${this.getIconForType(type)}</span>
            <span class="notification-message">${message}</span>
            <span class="notification-time">${this.formatTime(notification.timestamp)}</span>
        `;
        
        notification.element = element;
        
        // Auto-remove si tiene duración
        if (duration > 0) {
            setTimeout(() => {
                this.remove(notification.id);
            }, duration);
        }
        
        return notification;
    }
    
    addNotification(notification) {
        if (this.container) {
            // Insertar al principio
            this.container.insertBefore(notification.element, this.container.firstChild);
            
            // Agregar animación de entrada
            notification.element.style.opacity = '0';
            notification.element.style.transform = 'translateX(20px)';
            
            requestAnimationFrame(() => {
                notification.element.style.transition = 'all 0.3s ease';
                notification.element.style.opacity = '1';
                notification.element.style.transform = 'translateX(0)';
            });
        }
        
        this.notifications.unshift(notification);
        
        // Mantener límite de notificaciones
        while (this.notifications.length > this.maxNotifications) {
            const oldest = this.notifications.pop();
            if (oldest.element && oldest.element.parentNode) {
                oldest.element.remove();
            }
        }
        
        // Actualizar estado global
        TopologyApp.state.notifications = this.notifications;
    }
    
    remove(notificationId) {
        const index = this.notifications.findIndex(n => n.id === notificationId);
        if (index === -1) return;
        
        const notification = this.notifications[index];
        
        if (notification.element && notification.element.parentNode) {
            // Animación de salida
            notification.element.style.transition = 'all 0.3s ease';
            notification.element.style.opacity = '0';
            notification.element.style.transform = 'translateX(20px)';
            
            setTimeout(() => {
                if (notification.element && notification.element.parentNode) {
                    notification.element.remove();
                }
            }, 300);
        }
        
        this.notifications.splice(index, 1);
        TopologyApp.state.notifications = this.notifications;
    }
    
    clear() {
        this.notifications.forEach(notification => {
            if (notification.element && notification.element.parentNode) {
                notification.element.remove();
            }
        });
        
        this.notifications = [];
        TopologyApp.state.notifications = [];
        
        console.log('🧹 All notifications cleared');
    }
    
    getIconForType(type) {
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
    
    formatTime(date) {
        return date.toLocaleTimeString('es-ES', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

// Instancia global del sistema de notificaciones
window.notifications = new NotificationSystem();

// ================================
// UTILIDADES GENERALES
// ================================
function initializeUtils() {
    // Configurar timezone
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    console.log(`🌍 Timezone: ${timezone}`);
    
    // Configurar interceptores de errores globales
    window.addEventListener('unhandledrejection', function(event) {
        console.error('❌ Unhandled Promise Rejection:', event.reason);
        notifications.show('Error en la aplicación', 'danger');
    });
}

// Formateo de fechas
function formatDateTime(dateString, options = {}) {
    if (!dateString) return 'Never';
    
    try {
        const date = new Date(dateString);
        const defaultOptions = {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        };
        
        return date.toLocaleString('es-ES', { ...defaultOptions, ...options });
    } catch (error) {
        console.error('Error formatting date:', error);
        return 'Invalid Date';
    }
}

// Formateo de tiempo relativo
function formatTimeAgo(dateString) {
    if (!dateString) return 'Never';
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        
        const diffSeconds = Math.floor(diffMs / 1000);
        const diffMinutes = Math.floor(diffSeconds / 60);
        const diffHours = Math.floor(diffMinutes / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffSeconds < 60) return 'Just now';
        if (diffMinutes < 60) return `${diffMinutes}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return formatDateTime(dateString, { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
    } catch (error) {
        console.error('Error formatting time ago:', error);
        return 'Invalid Date';
    }
}

// Validación de CIDR
function validateCIDR(cidr) {
    const cidrRegex = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;
    
    if (!cidrRegex.test(cidr)) {
        return false;
    }
    
    const [ip, subnet] = cidr.split('/');
    const ipParts = ip.split('.');
    const subnetNum = parseInt(subnet);
    
    // Validar cada octeto del IP
    for (let part of ipParts) {
        const num = parseInt(part);
        if (num < 0 || num > 255) {
            return false;
        }
    }
    
    // Validar subnet
    if (subnetNum < 0 || subnetNum > 32) {
        return false;
    }
    
    return true;
}

// Debounce function
function debounce(func, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

// Throttle function
function throttle(func, delay) {
    let inThrottle;
    return function (...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, delay);
        }
    };
}

// ================================
// ESTADO DE LOADING GLOBAL
// ================================
class LoadingManager {
    constructor() {
        this.activeRequests = new Set();
    }
    
    start(requestId = null) {
        const id = requestId || 'request_' + Date.now();
        this.activeRequests.add(id);
        
        TopologyApp.state.isLoading = this.activeRequests.size > 0;
        this.updateGlobalLoadingState();
        
        return id;
    }
    
    stop(requestId) {
        if (requestId) {
            this.activeRequests.delete(requestId);
        }
        
        TopologyApp.state.isLoading = this.activeRequests.size > 0;
        this.updateGlobalLoadingState();
    }
    
    stopAll() {
        this.activeRequests.clear();
        TopologyApp.state.isLoading = false;
        this.updateGlobalLoadingState();
    }
    
    updateGlobalLoadingState() {
        const body = document.body;
        
        if (TopologyApp.state.isLoading) {
            body.classList.add('is-loading');
        } else {
            body.classList.remove('is-loading');
        }
    }
}

// Instancia global del gestor de loading
window.loadingManager = new LoadingManager();

// ================================
// MANEJO DE ERRORES
// ================================
function setupErrorHandling() {
    // Interceptar errores de red en fetch
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        const loadingId = loadingManager.start('fetch');
        
        try {
            const response = await originalFetch.apply(this, args);
            loadingManager.stop(loadingId);
            return response;
        } catch (error) {
            loadingManager.stop(loadingId);
            console.error('Network error:', error);
            
            if (!navigator.onLine) {
                notifications.show('Sin conexión a internet', 'warning');
            } else {
                notifications.show('Error de conexión', 'danger');
            }
            
            throw error;
        }
    };
    
    console.log('🛡️ Error handling setup complete');
}

// Función para manejo consistente de errores de API
function handleApiError(error, context = '') {
    console.error(`API Error ${context}:`, error);
    
    let message = 'Error desconocido';
    
    if (error.message.includes('timeout')) {
        message = 'Timeout - La operación tardó demasiado';
    } else if (error.message.includes('fetch')) {
        message = 'Error de conexión - Verifique la red';
    } else if (error.message.includes('404')) {
        message = 'Recurso no encontrado';
    } else if (error.message.includes('500')) {
        message = 'Error del servidor';
    } else if (error.message.includes('403')) {
        message = 'Acceso denegado';
    } else {
        message = error.message;
    }
    
    notifications.show(`${context ? context + ': ' : ''}${message}`, 'danger');
    return message;
}

// ================================
// UTILIDADES DE STORAGE LOCAL
// ================================
class LocalStorage {
    static set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.warn('LocalStorage set error:', error);
            return false;
        }
    }
    
    static get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.warn('LocalStorage get error:', error);
            return defaultValue;
        }
    }
    
    static remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.warn('LocalStorage remove error:', error);
            return false;
        }
    }
    
    static clear() {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.warn('LocalStorage clear error:', error);
            return false;
        }
    }
}

// ================================
// FUNCIONES GLOBALES EXPORTADAS
// ================================

// Exportar funciones principales para uso global
window.TopologyApp.utils = {
    formatDateTime,
    formatTimeAgo,
    validateCIDR,
    debounce,
    throttle,
    handleApiError
};

window.TopologyApp.storage = LocalStorage;

// Función para mostrar notificaciones (acceso rápido)
window.showNotification = function(message, type = 'info', duration = 5000) {
    return notifications.show(message, type, duration);
};

// Función para limpiar todos los estados
window.clearAppState = function() {
    loadingManager.stopAll();
    notifications.clear();
    
    // Limpiar intervalos
    Object.values(TopologyApp.intervals).forEach(interval => {
        if (interval) {
            clearInterval(interval);
        }
    });
    
    console.log('🧹 App state cleared');
};

// ================================
// DETECCIÓN DE CONECTIVIDAD
// ================================
window.addEventListener('online', function() {
    console.log('🌐 Connection restored');
    notifications.show('Conexión restaurada', 'success', 3000);
});

window.addEventListener('offline', function() {
    console.log('📡 Connection lost');
    notifications.show('Sin conexión a internet', 'warning', 0); // Sin auto-dismiss
});

// ================================
// CLEANUP AL SALIR
// ================================
window.addEventListener('beforeunload', function() {
    console.log('👋 Cleaning up before page unload');
    clearAppState();
});

console.log('✅ Global scripts initialized successfully');