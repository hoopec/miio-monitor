# Miio 设备监控系统

基于 python-miio 的小米 IoT 设备数据采集和可视化系统。

因为现在的米家智能插座都没有当日功率曲线，粒度只以日为单位，所以编写了这个项目获取24小时内功率变化。

## 功能特性

- 每 5 秒自动采集设备数据
- 数据保存到 SQLite 数据库，自动清理超过 24 小时的数据
- 支持多设备、多属性同时监控
- Web 界面实时显示数据曲线
- 响应式设计，支持手机和 PC 端访问
- 可切换 1/3/6/9/24 小时时间范围

## 安装依赖

```bash
pip install -r requirements.txt
```

`python-miio` 在本项目中默认使用 README 推荐的 git 方式安装（已写入 `requirements.txt`）：

```
pip install git+https://github.com/rytilahti/python-miio.git
```

## Docker 与 GitHub 自动构建

项目已支持通过 GitHub Actions 自动构建多架构 Docker 镜像：

- Workflow 文件：`.github/workflows/docker-image.yml`
- 目标架构：`linux/amd64`、`linux/arm64`
- 镜像仓库：`ghcr.io/hoopec/miio-monitor`
- 触发条件：推送到 `main/master`、推送 `v*` tag、手动触发

### 1) 直接拉取 Workflow 已构建镜像（推荐）

```bash
docker pull ghcr.io/hoopec/miio-monitor:latest
```

### 2) 使用 Docker 手动启动两个容器（collector + web）

先登录 GHCR（仓库为私有时需要）：

```bash
docker login ghcr.io
```

然后先确保已正确填写 `config.json`，并创建数据库文件：

```bash
python -c "open('data.db', 'a').close()"
```

先启动数据采集容器（collector）：

```bash
docker run -d \
  --name miio-collector \
  -v $(pwd)/config.json:/app/config.json:ro \
  -v $(pwd)/data.db:/app/data.db \
  ghcr.io/hoopec/miio-monitor:latest \
  python collector.py
```

再启动 Web 容器（web）：

```bash
docker run -d \
  --name miio-web \
  -p 5000:5000 \
  -v $(pwd)/config.json:/app/config.json:ro \
  -v $(pwd)/data.db:/app/data.db \
  ghcr.io/hoopec/miio-monitor:latest \
  python web_server.py
```

> Windows PowerShell 可把 `$(pwd)` 改为 `${PWD}`。

查看日志：

```bash
docker logs -f miio-collector
docker logs -f miio-web
```

停止并删除两个容器：

```bash
docker stop miio-web miio-collector
docker rm miio-web miio-collector
```

### 3) 使用 Docker Compose 启动（推荐）

`docker-compose.yml` 已改为直接使用 Workflow 发布的镜像（不再本地 build）。

首次使用前，建议先创建空数据库文件（避免挂载路径不存在）：

```bash
python -c "open('data.db', 'a').close()"
```

拉取镜像：

```bash
docker compose pull
```

启动：

```bash
docker compose up -d
```

查看日志：

```bash
docker compose logs -f
```

只看采集器日志：

```bash
docker compose logs -f collector
```

停止并清理容器：

```bash
docker compose down
```

访问地址：

- http://localhost:5000

### 4) Compose 文件说明

`docker-compose.yml` 核心内容：

- `collector` / `web` 都使用同一镜像：`ghcr.io/hoopec/miio-monitor:latest`
- `collector` 运行 `python collector.py`，`web` 运行 `python web_server.py`
- `collector` 和 `web` 共享 `config.json` 与 `data.db`
- `web` 暴露 `5000` 端口
- 都设置了 `restart: unless-stopped`

### 5) （可选）本地构建镜像用于调试

```bash
docker build -t miio-monitor:local .
```

## 配置说明

编辑 `config.json` 文件，配置你的设备信息：

```json
{
  "devices": [
    {
      "id": "device1",
      "name": "设备名称",
      "ip": "192.168.1.100",
      "token": "设备token",
      "model": "设备型号",
      "properties": [
        {"siid": 2, "piid": 1, "name": "温度", "unit": "°C"},
        {"siid": 2, "piid": 2, "name": "湿度", "unit": "%"}
      ]
    }
  ],
  "collection_interval": 5,
  "data_retention_hours": 24
}
```

### 获取设备信息

1. 获取设备 IP 和 token：

```
~ miiocli cloud
Username: example@example.com
Password:

== name of the device (Device offline ) ==
    Model: example.device.v1
    Token: b1946ac92492d2347c6235b4d2611184
    IP: 192.168.xx.xx (mac: ab:cd:ef:12:34:56)
    DID: 123456789
    Locale: cn
```

或

[Xiaomi-cloud-tokens-extractor](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor)

2. 获取设备属性（siid, piid）：

[https://home.miot-spec.com/](https://home.miot-spec.com/)

## 使用方法

#### 0.测试设备连接（可选）

配置完成后，先测试连接是否正常：

```bash
python test_connection.py
```

这会测试：

- 设备是否可以连接
- token 是否正确
- 属性（siid/piid）是否可以读取

### 1. 启动数据采集器

```bash
python collector.py
```

采集器会在后台持续运行，每 5 秒采集一次数据。

### 2. 启动 Web 服务器

```bash
python web_server.py
```

### 3. 访问 Web 界面

在浏览器中打开：
- PC 端：http://localhost:5000
- 手机端：http://<你的电脑IP>:5000

## 项目结构

```
project05/
├── collector.py                     # 数据采集器
├── web_server.py                    # Web 服务器
├── config.json                      # 配置文件
├── data.db                          # SQLite 数据库（自动创建）
├── requirements.txt                 # Python 依赖
├── Dockerfile                       # Docker 镜像构建文件
├── docker-compose.yml               # Docker Compose 编排
├── .github/workflows/docker-image.yml # GitHub 多架构镜像构建
├── templates/
│   └── index.html                  # Web 页面模板
└── static/
    ├── css/
    │   └── style.css               # 样式文件
    └── js/
        └── app.js                  # 前端逻辑
```

## 数据库结构

```sql
CREATE TABLE sensor_data (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    device_id TEXT,
    siid INTEGER,
    piid INTEGER,
    property_name TEXT,
    value REAL,
    unit TEXT
)
```

## 注意事项

1. 确保设备和运行程序的电脑在同一局域网内
2. 设备 token 需要通过 miiocli 工具获取
3. 不同型号设备的 siid 和 piid 可能不同，需要查询设备规格
4. 数据库会自动清理超过 24 小时的数据
5. Web 界面每 10 秒自动刷新数据
6. **同时运行两个脚本**：先启动采集器，再启动 Web 服务
7. **停止服务**：在窗口中按 Ctrl+C 或直接关闭窗口
8. **查看日志**：采集器窗口会实时显示采集状态

## 故障排查

### 无法连接设备
- 检查 IP 地址是否正确
- 检查 token 是否正确
- 确认设备和电脑在同一网络

### 无法获取属性
- 检查 siid 和 piid 是否正确
- 使用 miiocli 工具验证设备支持的属性

### Web 界面无数据
- 确认采集器正在运行
- 检查 data.db 文件是否存在
- 查看采集器日志输出

### 手机无法访问

- 确保电脑和手机在同一 WiFi
- 关闭电脑防火墙或允许 5000 端口
- 使用电脑的局域网 IP 地址
