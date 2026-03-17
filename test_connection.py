#!/usr/bin/env python3
"""
测试设备连接和配置
"""
import json
from miio.integrations.genericmiot.genericmiot import GenericMiot

def test_device_connection():
    print("=" * 50)
    print("Miio 设备连接测试")
    print("=" * 50)
    print()

    # 读取配置
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ 错误：未找到 config.json 文件")
        return
    except json.JSONDecodeError as e:
        print(f"❌ 错误：config.json 格式错误 - {e}")
        return

    devices = config.get('devices', [])
    if not devices:
        print("❌ 错误：config.json 中没有配置设备")
        return

    print(f"找到 {len(devices)} 个设备配置\n")

    # 测试每个设备
    for idx, device_config in enumerate(devices, 1):
        device_name = device_config.get('name', f'设备{idx}')
        device_ip = device_config.get('ip', '')
        device_token = device_config.get('token', '')
        device_model = device_config.get('model', '')

        print(f"[{idx}] 测试设备: {device_name}")
        print(f"    IP: {device_ip}")
        print(f"    Model: {device_model}")

        if not device_ip or not device_token:
            print("    ❌ 跳过：缺少 IP 或 token")
            print()
            continue

        if device_token == "your_token_here":
            print("    ⚠️  警告：请替换默认的 token")
            print()
            continue

        try:
            # 创建设备连接
            device = GenericMiot(
                ip=device_ip,
                token=device_token,
                model=device_model
            )

            # 测试获取设备信息
            info = device.info()
            print(f"    ✓ 连接成功")
            print(f"    设备信息: {info.model}")

            # 测试获取属性
            properties = device_config.get('properties', [])
            if properties:
                print(f"    测试 {len(properties)} 个属性:")
                for prop in properties[:3]:  # 只测试前3个
                    try:
                        result = device.get_property_by(
                            siid=prop['siid'],
                            piid=prop['piid']
                        )

                        # 处理返回结果
                        if isinstance(result, list) and len(result) > 0:
                            result = result[0]

                        # 提取实际值
                        if isinstance(result, dict):
                            value = result.get('value')
                            print(f"      ✓ {prop['name']}: {value} {prop.get('unit', '')} (原始: {result})")
                        else:
                            print(f"      ✓ {prop['name']}: {result} {prop.get('unit', '')}")

                    except Exception as e:
                        print(f"      ❌ {prop['name']}: {e}")

        except Exception as e:
            print(f"    ❌ 连接失败: {e}")

        print()

    print("=" * 50)
    print("测试完成")
    print("=" * 50)

if __name__ == '__main__':
    test_device_connection()
