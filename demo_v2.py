"""
InnoDB MVCC 可视化系统 v2.0 - 新功能演示脚本
展示隐藏字段和分屏对比视图功能
"""
import requests
import json
import time

API_BASE = 'http://localhost:5000/api'


def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


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
        row = result['row']
        print(f"✓ 事务 #{trx_id} 插入数据: {data}")
        print(f"  → 隐藏字段: DB_ROW_ID={row['row_id']}, DB_TRX_ID={row['trx_id']}, DB_ROLL_PTR={row['roll_pointer']}")
        return result['row_id']
    return None


def update_data(trx_id, row_id, data):
    """更新数据"""
    response = requests.post(f'{API_BASE}/data/update',
                            json={'trx_id': trx_id, 'row_id': row_id, 'data': data})
    result = response.json()
    if result['success']:
        print(f"✓ 事务 #{trx_id} 更新行 #{row_id}: {data}")
        # 获取更新后的行信息
        row_response = requests.get(f'{API_BASE}/row/{row_id}')
        row_data = row_response.json()
        row = row_data['row']
        print(f"  → 隐藏字段更新: DB_TRX_ID={row['trx_id']}, DB_ROLL_PTR={row['roll_pointer']}")
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


def get_transaction_info(trx_id):
    """获取事务信息"""
    response = requests.get(f'{API_BASE}/transaction/{trx_id}')
    return response.json()


def reset_system():
    """重置系统"""
    response = requests.post(f'{API_BASE}/system/reset')
    print("✓ 系统已重置")


def demo_hidden_fields():
    """演示隐藏字段的变化"""
    print_section("场景1: InnoDB 隐藏字段演示")

    reset_system()
    time.sleep(0.5)

    print("\n>>> 步骤1: 插入初始数据")
    trx1 = begin_transaction('READ_COMMITTED')
    row_id = insert_data(trx1, {'name': '张三', 'salary': 5000})
    commit_transaction(trx1)
    time.sleep(0.5)

    print("\n>>> 步骤2: 第一次更新数据")
    trx2 = begin_transaction('READ_COMMITTED')
    update_data(trx2, row_id, {'name': '张三', 'salary': 6000})
    commit_transaction(trx2)
    time.sleep(0.5)

    print("\n>>> 步骤3: 第二次更新数据")
    trx3 = begin_transaction('READ_COMMITTED')
    update_data(trx3, row_id, {'name': '张三', 'salary': 7000})
    commit_transaction(trx3)
    time.sleep(0.5)

    print("\n>>> 步骤4: 第三次更新数据")
    trx4 = begin_transaction('READ_COMMITTED')
    update_data(trx4, row_id, {'name': '张三', 'salary': 8000})
    commit_transaction(trx4)

    print("\n📌 观察要点:")
    print("   1. 每次更新后，DB_TRX_ID 都会变成当前事务的ID")
    print("   2. DB_ROLL_PTR 指向上一个版本的 Undo Log")
    print("   3. DB_ROW_ID 始终保持不变")
    print("\n💡 请在Web界面中查看数据行，可以看到突出显示的隐藏字段！")


def demo_split_view_read_committed():
    """演示分屏对比视图 - READ COMMITTED"""
    print_section("场景2: 分屏对比 - READ COMMITTED 不可重复读")

    reset_system()
    time.sleep(0.5)

    print("\n>>> 步骤1: 开启两个 READ_COMMITTED 事务")
    trx1 = begin_transaction('READ_COMMITTED')
    trx2 = begin_transaction('READ_COMMITTED')

    print("\n>>> 步骤2: 事务1插入数据（不提交）")
    row_id = insert_data(trx1, {'product': 'iPhone', 'price': 5999})

    print("\n>>> 步骤3: 事务2尝试读取")
    read_data(trx2, row_id)

    print("\n>>> 步骤4: 提交事务1")
    commit_transaction(trx1)
    time.sleep(0.5)

    print("\n>>> 步骤5: 事务2再次读取")
    read_data(trx2, row_id)

    print("\n📌 分屏对比观察:")
    print("   1. 切换到分屏模式")
    print("   2. 选择事务1和事务2进行对比")
    print("   3. 观察：")
    print("      - 事务1能看到自己插入的数据")
    print("      - 事务2在事务1提交前看不到数据")
    print("      - 事务2在事务1提交后能看到数据（不可重复读）")

    commit_transaction(trx2)


def demo_split_view_repeatable_read():
    """演示分屏对比视图 - REPEATABLE READ"""
    print_section("场景3: 分屏对比 - REPEATABLE READ 可重复读")

    reset_system()
    time.sleep(0.5)

    print("\n>>> 步骤1: 开启两个 REPEATABLE_READ 事务")
    trx1 = begin_transaction('REPEATABLE_READ')
    trx2 = begin_transaction('REPEATABLE_READ')

    print("\n>>> 步骤2: 事务1插入数据（不提交）")
    row_id = insert_data(trx1, {'product': 'iPad', 'price': 3999})

    print("\n>>> 步骤3: 事务2尝试读取")
    read_data(trx2, row_id)

    print("\n>>> 步骤4: 提交事务1")
    commit_transaction(trx1)
    time.sleep(0.5)

    print("\n>>> 步骤5: 事务2再次读取")
    read_data(trx2, row_id)

    print("\n📌 分屏对比观察:")
    print("   1. 切换到分屏模式")
    print("   2. 选择事务1和事务2进行对比")
    print("   3. 观察：")
    print("      - 事务1能看到自己插入的数据")
    print("      - 事务2在事务1提交前看不到数据")
    print("      - 事务2在事务1提交后仍然看不到数据（可重复读）")
    print("   4. 查看 ReadView:")
    print("      - 事务2的 m_ids 包含事务1的ID")
    print("      - 根据可见性规则，事务1的数据对事务2不可见")

    commit_transaction(trx2)


def demo_split_view_mvcc():
    """演示分屏对比视图 - MVCC 可见性规则"""
    print_section("场景4: 分屏对比 - MVCC 可见性规则详解")

    reset_system()
    time.sleep(0.5)

    print("\n>>> 步骤1: 事务1插入数据并提交")
    trx1 = begin_transaction('REPEATABLE_READ')
    row_id = insert_data(trx1, {'user': '李四', 'balance': 1000})
    commit_transaction(trx1)
    time.sleep(0.5)

    print("\n>>> 步骤2: 开启事务2和事务3")
    trx2 = begin_transaction('REPEATABLE_READ')
    trx3 = begin_transaction('REPEATABLE_READ')

    print("\n>>> 步骤3: 两个事务都能看到已提交的数据")
    read_data(trx2, row_id)
    read_data(trx3, row_id)

    print("\n>>> 步骤4: 事务2更新数据（不提交）")
    update_data(trx2, row_id, {'user': '李四', 'balance': 1500})

    print("\n>>> 步骤5: 事务3尝试读取")
    read_data(trx3, row_id)

    print("\n>>> 步骤6: 事务2读取自己的修改")
    read_data(trx2, row_id)

    print("\n📌 分屏对比观察:")
    print("   1. 切换到分屏模式")
    print("   2. 选择事务2和事务3进行对比")
    print("   3. 观察数据行的隐藏字段:")
    print("      - DB_TRX_ID = 2 (事务2修改的)")
    print("      - DB_ROLL_PTR 指向旧版本")
    print("   4. 观察可见性:")
    print("      - 事务2: 能看到自己的修改 (balance=1500)")
    print("      - 事务3: 看到旧版本 (balance=1000)")
    print("   5. 理解可见性规则:")
    print("      - 事务2: trx_id == creator_trx_id → 可见")
    print("      - 事务3: trx_id=2 在 m_ids 中 → 不可见，回溯到旧版本")

    commit_transaction(trx2)
    commit_transaction(trx3)


def demo_complex_scenario():
    """演示复杂场景 - 多个事务并发操作"""
    print_section("场景5: 复杂场景 - 多事务并发与版本链")

    reset_system()
    time.sleep(0.5)

    print("\n>>> 步骤1: 创建初始数据")
    trx0 = begin_transaction('REPEATABLE_READ')
    row1 = insert_data(trx0, {'account': 'A', 'balance': 1000})
    row2 = insert_data(trx0, {'account': 'B', 'balance': 2000})
    commit_transaction(trx0)
    time.sleep(0.5)

    print("\n>>> 步骤2: 开启3个并发事务")
    trx1 = begin_transaction('REPEATABLE_READ')
    trx2 = begin_transaction('REPEATABLE_READ')
    trx3 = begin_transaction('REPEATABLE_READ')

    print("\n>>> 步骤3: 事务1更新账户A")
    update_data(trx1, row1, {'account': 'A', 'balance': 1200})

    print("\n>>> 步骤4: 事务2更新账户B")
    update_data(trx2, row2, {'account': 'B', 'balance': 2500})

    print("\n>>> 步骤5: 事务3读取所有数据")
    print("事务3读取账户A:")
    read_data(trx3, row1)
    print("事务3读取账户B:")
    read_data(trx3, row2)

    print("\n>>> 步骤6: 提交事务1")
    commit_transaction(trx1)
    time.sleep(0.5)

    print("\n>>> 步骤7: 事务3再次读取（应该看到相同的数据）")
    print("事务3读取账户A:")
    read_data(trx3, row1)
    print("事务3读取账户B:")
    read_data(trx3, row2)

    print("\n>>> 步骤8: 开启事务4（新事务）")
    trx4 = begin_transaction('REPEATABLE_READ')
    print("事务4读取账户A:")
    read_data(trx4, row1)
    print("事务4读取账户B:")
    read_data(trx4, row2)

    print("\n📌 分屏对比观察:")
    print("   1. 对比事务3和事务4:")
    print("      - 事务3: 看到旧版本 (A=1000, B=2000)")
    print("      - 事务4: 看到新版本 (A=1200, B=2000)")
    print("   2. 观察隐藏字段:")
    print("      - 账户A的 DB_TRX_ID = 1")
    print("      - 账户B的 DB_TRX_ID = 2")
    print("   3. 点击数据行查看版本链:")
    print("      - 可以看到完整的版本演变历史")
    print("      - 每个版本都有对应的 Undo Log")

    commit_transaction(trx2)
    commit_transaction(trx3)
    commit_transaction(trx4)


def main():
    """主函数"""
    print("\n" + "🎯" * 35)
    print("  InnoDB MVCC 可视化系统 v2.0 - 新功能演示")
    print("🎯" * 35)

    print("\n💡 提示: 请确保Web服务器已启动 (http://localhost:5002)")
    print("   在浏览器中打开Web界面，可以实时查看系统状态变化\n")

    print("📋 本次演示包含以下场景:")
    print("   1. InnoDB 隐藏字段演示")
    print("   2. 分屏对比 - READ COMMITTED 不可重复读")
    print("   3. 分屏对比 - REPEATABLE READ 可重复读")
    print("   4. 分屏对比 - MVCC 可见性规则详解")
    print("   5. 复杂场景 - 多事务并发与版本链")

    input("\n按回车键开始演示...")

    try:
        # 场景1: 隐藏字段
        demo_hidden_fields()
        input("\n按回车键继续下一个场景...")

        # 场景2: READ COMMITTED
        demo_split_view_read_committed()
        input("\n按回车键继续下一个场景...")

        # 场景3: REPEATABLE READ
        demo_split_view_repeatable_read()
        input("\n按回车键继续下一个场景...")

        # 场景4: MVCC 可见性
        demo_split_view_mvcc()
        input("\n按回车键继续下一个场景...")

        # 场景5: 复杂场景
        demo_complex_scenario()

        print_section("演示完成")
        print("\n✅ 所有演示场景已完成！")
        print("\n💡 建议:")
        print("   1. 在Web界面中切换到分屏模式")
        print("   2. 选择不同的事务进行对比")
        print("   3. 观察隐藏字段的变化")
        print("   4. 点击数据行查看版本链")
        print("   5. 理解 MVCC 的可见性规则")
        print("\n🎓 学习要点:")
        print("   • DB_TRX_ID: 标识最后修改该行的事务")
        print("   • DB_ROLL_PTR: 连接版本链的关键")
        print("   • ReadView: 决定数据可见性的核心")
        print("   • 分屏对比: 直观理解事务隔离")

    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到服务器")
        print("   请确保Flask应用已启动: python app.py")
    except Exception as e:
        print(f"\n❌ 错误: {e}")


if __name__ == '__main__':
    main()
