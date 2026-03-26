#!/usr/bin/env python3
"""
Web 服务器 - 提供数据查询和可视化界面
"""
from flask import Flask, render_template, jsonify, request
import sqlite3
import json
import logging
import os
import time
from datetime import datetime, timedelta

app = Flask(__name__)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv('DB_PATH', 'data.db')
DB_TIMEOUT_SECONDS = 30
DB_BUSY_TIMEOUT_MS = 30000
LOCK_RETRY_TIMES = 5
LOCK_RETRY_BASE_DELAY = 0.1

def load_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT_SECONDS)
    conn.execute(f'PRAGMA busy_timeout={DB_BUSY_TIMEOUT_MS}')
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.row_factory = sqlite3.Row
    return conn


def fetch_all_with_retry(query, params):
    for attempt in range(LOCK_RETRY_TIMES):
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except sqlite3.OperationalError as e:
            if 'locked' not in str(e).lower() or attempt == LOCK_RETRY_TIMES - 1:
                raise
            wait_seconds = LOCK_RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(f"数据库忙，{wait_seconds:.1f} 秒后重试查询")
            time.sleep(wait_seconds)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/devices')
def get_devices():
    config = load_config()
    devices = []
    for device in config['devices']:
        devices.append({
            'id': device['id'],
            'name': device['name'],
            'properties': [
                {
                    'siid': prop['siid'],
                    'piid': prop['piid'],
                    'name': prop['name'],
                    'unit': prop.get('unit', '')
                }
                for prop in device['properties']
            ]
        })
    return jsonify(devices)

@app.route('/api/data')
def get_data():
    device_id = request.args.get('device_id')
    siid = request.args.get('siid', type=int)
    piid = request.args.get('piid', type=int)
    hours = request.args.get('hours', default=24, type=int)

    if not device_id or siid is None or piid is None:
        return jsonify({'error': '缺少必要参数'}), 400

    start_time = (datetime.now() - timedelta(hours=hours)).isoformat()

    try:
        rows = fetch_all_with_retry('''
            SELECT timestamp, value, property_name, unit
            FROM sensor_data
            WHERE device_id = ? AND siid = ? AND piid = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        ''', (device_id, siid, piid, start_time))
    except sqlite3.OperationalError:
        return jsonify({'error': '数据库忙，请稍后重试'}), 503

    data = {
        'timestamps': [row['timestamp'] for row in rows],
        'values': [row['value'] for row in rows],
        'property_name': rows[0]['property_name'] if rows else '',
        'unit': rows[0]['unit'] if rows else ''
    }

    return jsonify(data)

@app.route('/api/latest')
def get_latest():
    device_id = request.args.get('device_id')

    if not device_id:
        return jsonify({'error': '缺少设备ID'}), 400

    try:
        rows = fetch_all_with_retry('''
            SELECT device_id, siid, piid, property_name, value, unit, timestamp
            FROM sensor_data
            WHERE device_id = ?
            AND timestamp = (
                SELECT MAX(timestamp)
                FROM sensor_data AS sd2
                WHERE sd2.device_id = sensor_data.device_id
                AND sd2.siid = sensor_data.siid
                AND sd2.piid = sensor_data.piid
            )
            ORDER BY siid, piid
        ''', (device_id,))
    except sqlite3.OperationalError:
        return jsonify({'error': '数据库忙，请稍后重试'}), 503

    latest_data = [
        {
            'siid': row['siid'],
            'piid': row['piid'],
            'name': row['property_name'],
            'value': row['value'],
            'unit': row['unit'],
            'timestamp': row['timestamp']
        }
        for row in rows
    ]

    return jsonify(latest_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
