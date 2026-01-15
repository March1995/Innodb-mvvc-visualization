"""
InnoDB MVCC 可视化系统演示脚本
展示常见的MVCC场景
"""
import requests
import json
import time

API_BASE = 'http://localhost:5001/api'


def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def begin_transaction(isolation_level='READ_COMMITTED'):
    """开启事务"""
    response = requests.post(f'{API_BASE}/transaction/begin',
                            json={'isolation_level': isolation_level})
    result = response.json()
    print(f"✓ 开启事务 #{result['trx_id']} (隔离级别: {isolation_level})")
    return result['trx_id']


def commit_transaction(trx_id):
    """提交事务"""
    response = requests.post(f'{API_BASE}/transaction/commit',
                            json={'trx_id': trx_id})
    result = response.json()
    if result['success']:
        print(f"✓ 提交事务 #{trx_id}")
    return result['success']


def insert_data(trx_id, data):
    """插入数据"""
    response = requests.post(f'{API_BASE}/data/insert',
                            json={'trx_id': trx_id, 'data': data})
    result = response.json()
    if result['success']:
        print(f"✓ 事务 #{trx_id} 插入数据: {data} -> 行ID: {result['row_id']}")
        return result['row_id']
    return None


def update_data(trx_id, row_id, data):
    """更新数据"""
    response = requests.post(f'{API_BASE}/data/update',
                            json={'trx_id': trx_id, 'row_id': row_id, 'data': data})
    result = response.json()
    if result['success']:
        print(f"✓ 事务 #{trx_id} 更新行 #{row_id}: {data}")
    return result['success']


def read_data(trx_id, row_id):
    """读取数据"""
    response = requests.post(f'{API_BASE}/data/read',
                            json={'trx_id': trx_id, 'row_id': row_id})
    result = response.json()
    if result['success']:
        if result['data']:
            print(f"✓ 事务 #{trx_id} 读取行 #{row_id}: {result['data']}")
        else:
            print(f"✗ 事务 #{trx_id} 无法看到行 #{row_id} (不可见)")
    return result.get('data')


def get_system_state():
    """获取系统状态"""
    response = requests.get(f'{API_BASE}/system/state')
    return response.json()


def reset_system():
    """重置系统"""
    response = requests.post(f'{API_BASE}/system/reset')
    print("✓ 系统已重置")


def demo_read_committed():
    """演示 READ COMMITTED 隔离级别"""
    print_section("场景1: READ COMMITTED - 不可重复读")

    # 重置系统
    reset_system()
    time.sleep(0.5)

    # 事务1插入数据
    trx1 = begin_transaction('READ_COMMITTED')
    row_id = insert_data(trx1, {'name': '张三', 'salary': 5000})

    # 事务2尝试读取
    trx2 = begin_transaction('READ_COMMITTED')
    print("\n>>> 事务2尝试读取（事务1未提交）:")
    read_data(trx2, row_id)

    # 提交事务1
    print("\n>>> 提交事务1:")
    commit_transaction(trx1)
    time.sleep(0.5)

    # 事务2再次读取
    print("\n>>> 事务2再次读取（事务1已提交）:")
    read_data(trx2, row_id)

    print("\n📌 结论: READ COMMITTED 会出现不可重复读现象")
    print("   事务2在同一个事务中两次读取，结果不同")

    commit_transaction(trx2)


def demo_repeatable_read():
    """演示 REPEATABLE READ 隔离级别"""
    print_section("场景2: REPEATABLE READ - 可重复读")

    # 重置系统
    reset_system()
    time.sleep(0.5)

    # 事务1插入数据
    trx1 = begin_transaction('REPEATABLE_READ')
    row_id = insert_data(trx1, {'name': '李四', 'salary': 6000})

    # 事务2尝试读取
    trx2 = begin_transaction('REPEATABLE_READ')
    print("\n>>> 事务2尝试读取（事务1未提交）:")
    read_data(trx2, row_id)

    # 提交事务1
    print("\n>>> 提交事务1:")
    commit_transaction(trx1)
    time.sleep(0.5)

    # 事务2再次读取
    print("\n>>> 事务2再次读取（事务1已提交）:")
    read_data(trx2, row_id)

    print("\n📌 结论: REPEATABLE READ 保证可重复读")
    print("   事务2在同一个事务中多次读取，结果一致")

    commit_transaction(trx2)


def demo_version_chain():
    """演示版本链和Undo Log"""
    print_section("场景3: 版本链和Undo Log")

    # 重置系统
    reset_system()
    time.sleep(0.5)

    # 事务1插入数据
    trx1 = begin_transaction('READ_COMMITTED')
    row_id = insert_data(trx1, {'name': '王五', 'salary': 5000, 'dept': '技术部'})
    commit_transaction(trx1)
    time.sleep(0.5)

    # 事务2更新数据
    trx2 = begin_transaction('READ_COMMITTED')
    update_data(trx2, row_id, {'name': '王五', 'salary': 6000, 'dept': '技术部'})
    commit_transaction(trx2)
    time.sleep(0.5)

    # 事务3再次更新
    trx3 = begin_transaction('READ_COMMITTED')
    update_data(trx3, row_id, {'name': '王五', 'salary': 7000, 'dept': '产品部'})
    commit_transaction(trx3)
    time.sleep(0.5)

    # 事务4再次更新
    trx4 = begin_transaction('READ_COMMITTED')
    update_data(trx4, row_id, {'name': '王五', 'salary': 8000, 'dept': '产品部'})
    commit_transaction(trx4)

    print("\n📌 结论: 数据行形成了完整的版本链")
    print("   每次更新都会创建新的Undo Log记录")
    print("   通过roll_pointer连接所有历史版本")
    print("\n💡 请在Web界面中点击该数据行，查看完整的版本链！")


def demo_mvcc_visibility():
    """演示MVCC可见性判断"""
    print_section("场景4: MVCC可见性判断")

    # 重置系统
    reset_system()
    time.sleep(0.5)

    # 事务1插入数据
    trx1 = begin_transaction('REPEATABLE_READ')
    row_id = insert_data(trx1, {'name': '赵六', 'age': 28})
    commit_transaction(trx1)
    time.sleep(0.5)

    # 开启事务2和事务3
    trx2 = begin_transaction('REPEATABLE_READ')
    trx3 = begin_transaction('REPEATABLE_READ')

    print("\n>>> 事务2和事务3都能看到已提交的数据:")
    read_data(trx2, row_id)
    read_data(trx3, row_id)

    # 事务2更新数据（但不提交）
    print("\n>>> 事务2更新数据（未提交）:")
    update_data(trx2, row_id, {'name': '赵六', 'age': 29})

    # 事务3尝试读取
    print("\n>>> 事务3尝试读取:")
    read_data(trx3, row_id)

    # 事务2读取自己的修改
    print("\n>>> 事务2读取自己的修改:")
    read_data(trx2, row_id)

    print("\n📌 结论: MVCC通过ReadView实现事务隔离")
    print("   - 事务3看不到事务2未提交的修改")
    print("   - 事务2能看到自己的修改")

    commit_transaction(trx2)
    commit_transaction(trx3)


def demo_concurrent_transactions():
    """演示并发事务场景"""
    print_section("场景5: 并发事务操作")

    # 重置系统
    reset_system()
    time.sleep(0.5)

    # 创建初始数据
    trx0 = begin_transaction('READ_COMMITTED')
    row1 = insert_data(trx0, {'product': 'iPhone', 'stock': 100})
    row2 = insert_data(trx0, {'product': 'iPad', 'stock': 50})
    commit_transaction(trx0)
    time.sleep(0.5)

    # 开启多个并发事务
    print("\n>>> 开启3个并发事务:")
    trx1 = begin_transaction('REPEATABLE_READ')
    trx2 = begin_transaction('REPEATABLE_READ')
    trx3 = begin_transaction('REPEATABLE_READ')

    # 各个事务进行不同的操作
    print("\n>>> 事务1: 更新iPhone库存")
    update_data(trx1, row1, {'product': 'iPhone', 'stock': 95})

    print("\n>>> 事务2: 更新iPad库存")
    update_data(trx2, row2, {'product': 'iPad', 'stock': 45})

    print("\n>>> 事务3: 读取所有数据")
    read_data(trx3, row1)
    read_data(trx3, row2)

    print("\n>>> 提交事务1和事务2:")
    commit_transaction(trx1)
    commit_transaction(trx2)
    time.sleep(0.5)

    print("\n>>> 事务3再次读取（REPEATABLE READ保证一致性）:")
    read_data(trx3, row1)
    read_data(trx3, row2)

    commit_transaction(trx3)

    print("\n📌 结论: MVCC支持高并发事务")
    print("   - 多个事务可以同时操作不同的数据行")
    print("   - REPEATABLE READ保证事务内的一致性读")


def main():
    """主函数"""
    print("\n" + "🎯" * 30)
    print("  InnoDB MVCC 可视化系统 - 演示脚本")
    print("🎯" * 30)

    print("\n💡 提示: 请确保Web服务器已启动 (http://localhost:5001)")
    print("   在浏览器中打开Web界面，可以实时查看系统状态变化\n")

    input("按回车键开始演示...")

    try:
        # 场景1: READ COMMITTED
        demo_read_committed()
        input("\n按回车键继续下一个场景...")

        # 场景2: REPEATABLE READ
        demo_repeatable_read()
        input("\n按回车键继续下一个场景...")

        # 场景3: 版本链
        demo_version_chain()
        input("\n按回车键继续下一个场景...")

        # 场景4: MVCC可见性
        demo_mvcc_visibility()
        input("\n按回车键继续下一个场景...")

        # 场景5: 并发事务
        demo_concurrent_transactions()

        print_section("演示完成")
        print("\n✅ 所有演示场景已完成！")
        print("\n💡 建议:")
        print("   1. 在Web界面中查看完整的系统状态")
        print("   2. 点击数据行查看版本链")
        print("   3. 查看ReadView和Undo Log面板")
        print("   4. 尝试手动操作，体验MVCC机制")

    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到服务器")
        print("   请确保Flask应用已启动: python app.py")
    except Exception as e:
        print(f"\n❌ 错误: {e}")


if __name__ == '__main__':
    main()
