let devices = [];
let currentDevice = null;
let currentProperty = null;
let currentHours = 1;
let chart = null;
let refreshInterval = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadDevices();
    setupEventListeners();
});

// 加载设备列表
async function loadDevices() {
    try {
        const response = await fetch('/api/devices');
        devices = await response.json();

        const deviceSelect = document.getElementById('deviceSelect');
        deviceSelect.innerHTML = '<option value="">请选择设备</option>';

        devices.forEach(device => {
            const option = document.createElement('option');
            option.value = device.id;
            option.textContent = device.name;
            deviceSelect.appendChild(option);
        });

        updateStatus('设备列表加载完成');
    } catch (error) {
        updateStatus('加载设备列表失败: ' + error.message);
    }
}

// 设置事件监听
function setupEventListeners() {
    document.getElementById('deviceSelect').addEventListener('change', onDeviceChange);
    document.getElementById('propertySelect').addEventListener('change', onPropertyChange);

    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentHours = parseInt(e.target.dataset.hours);
            if (currentDevice && currentProperty) {
                loadChartData();
            }
        });
    });
}

// 设备选择变化
function onDeviceChange(e) {
    const deviceId = e.target.value;
    if (!deviceId) {
        document.getElementById('propertySelect').innerHTML = '<option value="">请先选择设备</option>';
        return;
    }

    currentDevice = devices.find(d => d.id === deviceId);
    const propertySelect = document.getElementById('propertySelect');
    propertySelect.innerHTML = '<option value="">请选择属性</option>';

    currentDevice.properties.forEach(prop => {
        const option = document.createElement('option');
        option.value = JSON.stringify({siid: prop.siid, piid: prop.piid});
        option.textContent = `${prop.name} (${prop.unit})`;
        propertySelect.appendChild(option);
    });

    loadLatestValues(deviceId);
}

// 属性选择变化
function onPropertyChange(e) {
    const value = e.target.value;
    if (!value) return;

    currentProperty = JSON.parse(value);
    loadChartData();
    startAutoRefresh();
}

// 加载最新值
async function loadLatestValues(deviceId) {
    try {
        const response = await fetch(`/api/latest?device_id=${deviceId}`);
        const data = await response.json();

        const container = document.getElementById('latestValues');
        if (data.length === 0) {
            container.style.display = 'none';
            return;
        }

        container.classList.add('show');
        container.innerHTML = `
            <h3>当前数值</h3>
            <div class="latest-grid">
                ${data.map(item => `
                    <div class="latest-item">
                        <div class="label">${item.name}</div>
                        <div class="value">
                            ${item.value !== null ? item.value.toFixed(2) : 'N/A'}
                            <span class="unit">${item.unit}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        console.error('加载最新值失败:', error);
    }
}

// 加载图表数据
async function loadChartData() {
    if (!currentDevice || !currentProperty) return;

    updateStatus('正在加载数据...');

    try {
        const url = `/api/data?device_id=${currentDevice.id}&siid=${currentProperty.siid}&piid=${currentProperty.piid}&hours=${currentHours}`;
        const response = await fetch(url);
        const data = await response.json();

        if (data.error) {
            updateStatus('错误: ' + data.error);
            return;
        }

        renderChart(data);
        updateStatus(`显示最近 ${currentHours} 小时的数据 (共 ${data.values.length} 个数据点)`);
    } catch (error) {
        updateStatus('加载数据失败: ' + error.message);
    }
}

// 渲染图表
function renderChart(data) {
    const ctx = document.getElementById('dataChart').getContext('2d');

    if (chart) {
        chart.destroy();
    }

    const labels = data.timestamps.map(ts => {
        const date = new Date(ts);
        return date.toLocaleString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    });

    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: `${data.property_name} (${data.unit})`,
                data: data.values,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 2,
                pointHoverRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: '时间'
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: data.unit
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// 自动刷新
function startAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }

    refreshInterval = setInterval(() => {
        if (currentDevice && currentProperty) {
            loadChartData();
            loadLatestValues(currentDevice.id);
        }
    }, 10000); // 每10秒刷新一次
}

// 更新状态
function updateStatus(message) {
    document.getElementById('status').textContent = message;
}
