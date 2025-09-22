let isScanning = false;

// Cargar configuración actual al inicio
window.onload = function () {
    checkCurrentConfig();
};

function setNetwork(network) {
    document.getElementById('network').value = network;
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    statusDiv.className = `status ${type}`;
    statusDiv.style.display = 'block';

    if (type !== 'loading') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 5000);
    }
}

async function checkCurrentConfig() {
    try {
        const response = await fetch('/status');
        const data = await response.json();

        document.getElementById('currentNetwork').textContent =
            `Red configurada: ${data.target_network || 'No configurada'} | ` +
            `Últimos escaneos: ${data.last_scan_count || 0} archivos`;

    } catch (error) {
        document.getElementById('currentNetwork').textContent = 'Error cargando configuración';
    }
}

async function checkStatus() {
    try {
        showStatus('Consultando estado del scanner...', 'loading');

        const response = await fetch('/status');
        const data = await response.json();

        let statusMessage = `Red: ${data.target_network || 'No configurada'}\n`;
        statusMessage += `Escaneos realizados: ${data.last_scan_count || 0}\n`;
        statusMessage += `Topología disponible: ${data.topology_available ? 'Sí' : 'No'}\n`;

        if (data.last_scan_time) {
            statusMessage += `Último escaneo: ${new Date(data.last_scan_time).toLocaleString()}`;
        }

        showStatus(statusMessage, 'success');

    } catch (error) {
        showStatus('Error consultando estado: ' + error.message, 'error');
    }
}

document.getElementById('scanForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    if (isScanning) {
        showStatus('Ya hay un escaneo en progreso. Espere...', 'error');
        return;
    }

    const network = document.getElementById('network').value.trim();
    const scanType = document.getElementById('scanType').value;

    if (!network) {
        showStatus('Por favor ingrese una red válida', 'error');
        return;
    }

    // Validación básica de CIDR
    const cidrPattern = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;
    if (!cidrPattern.test(network)) {
        showStatus('Formato de red inválido. Use formato CIDR (ej: 192.168.1.0/24)', 'error');
        return;
    }

    isScanning = true;
    const submitBtn = document.querySelector('.btn-scan');
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ Escaneando...';

    try {
        let requests = [];

        if (scanType === 'ports' || scanType === 'both') {
            showStatus(`Iniciando escaneo de puertos en ${network}...`, 'loading');
            requests.push(
                fetch('/scan', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ network: network })
                })
            );
        }

        if (scanType === 'topology' || scanType === 'both') {
            showStatus(`Iniciando mapeo topológico en ${network}...`, 'loading');
            requests.push(
                fetch('/topology', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ network: network })
                })
            );
        }

        const responses = await Promise.all(requests);

        // Verificar si todas las respuestas fueron exitosas
        const allSuccessful = responses.every(response => response.ok);

        if (allSuccessful) {
            showStatus(`✅ Escaneo iniciado exitosamente en ${network}. Los resultados aparecerán en unos minutos.`, 'success');
            checkCurrentConfig(); // Actualizar configuración
        } else {
            throw new Error('Algunos escaneos fallaron');
        }

    } catch (error) {
        showStatus('❌ Error iniciando escaneo: ' + error.message, 'error');
    } finally {
        isScanning = false;
        submitBtn.disabled = false;
        submitBtn.textContent = '🚀 Iniciar Escaneo';
    }
});