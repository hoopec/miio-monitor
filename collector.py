#!/usr/bin/env python3
"""
miio 数据采集器
每隔指定时间采集设备数据并存储到 SQLite 数据库
"""
import json
import time
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from miio.integrations.genericmiot.genericmiot import GenericMiot
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MiioCollector:
    def __init__(self, config_path='config.json', db_path='data.db'):
        self.config_path = config_path
        self.db_path = db_path
        self.config = self.load_config()
        self.init_database()

    def load_config(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                device_id TEXT NOT NULL,
                siid INTEGER NOT NULL,
                piid INTEGER NOT NULL,
                property_name TEXT,
                value REAL,
                unit TEXT
            )
        ''')

        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON sensor_data(timestamp)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_device
            ON sensor_data(device_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_device_property
            ON sensor_data(device_id, siid, piid)
        ''')

        conn.commit()
        conn.close()
        logger.info("数据库初始化完成")

    def collect_device_data(self, device_config):
        device_id = device_config['id']
        try:
            device = GenericMiot(
                ip=device_config['ip'],
                token=device_config['token'],
                model=device_config['model']
            )

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()

            for prop in device_config['properties']:
                try:
                    result = device.get_property_by(
                        siid=prop['siid'],
                        piid=prop['piid']
                    )

                    # 处理返回结果，提取实际值
                    if isinstance(result, list) and len(result) > 0:
                        result = result[0]

                    # 如果返回的是字典（包含 'value' 字段），提取值
                    if isinstance(result, dict):
                        value = result.get('value')
                    else:
                        value = result

                    # 转换布尔值为整数
                    if isinstance(value, bool):
                        value = 1 if value else 0
                    # 确保值是数值类型
                    elif value is not None and not isinstance(value, (int, float)):
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            logger.warning(f"无法转换值为数值: {value}")
                            continue

                    cursor.execute('''
                        INSERT INTO sensor_data
                        (timestamp, device_id, siid, piid, property_name, value, unit)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        timestamp,
                        device_id,
                        prop['siid'],
                        prop['piid'],
                        prop['name'],
                        value,
                        prop.get('unit', '')
                    ))

                    logger.info(f"{device_config['name']} - {prop['name']}: {value} {prop.get('unit', '')}")

                except Exception as e:
                    logger.error(f"获取 {device_config['name']} 属性 {prop['name']} 失败: {e}")

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"连接设备 {device_config['name']} 失败: {e}")

    def cleanup_old_data(self):
        retention_hours = self.config.get('data_retention_hours', 24)
        cutoff_time = (datetime.now() - timedelta(hours=retention_hours)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sensor_data WHERE timestamp < ?', (cutoff_time,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted > 0:
            logger.info(f"清理了 {deleted} 条超过 {retention_hours} 小时的旧数据")

    def run(self):
        interval = self.config.get('collection_interval', 5)
        logger.info(f"开始数据采集，间隔 {interval} 秒")

        cleanup_counter = 0
        while True:
            try:
                for device in self.config['devices']:
                    self.collect_device_data(device)

                cleanup_counter += 1
                if cleanup_counter >= 720:  # 每小时清理一次（720 * 5秒 = 1小时）
                    self.cleanup_old_data()
                    cleanup_counter = 0

                time.sleep(interval)

            except KeyboardInterrupt:
                logger.info("收到停止信号，退出采集")
                break
            except Exception as e:
                logger.error(f"采集过程出错: {e}")
                time.sleep(interval)

if __name__ == '__main__':
    collector = MiioCollector()
    collector.run()
