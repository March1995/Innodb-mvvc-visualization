#!/usr/bin/env python3
"""
InnoDB MVCC 可视化系统 - 演示场景
展示各种典型的 MVCC 场景
"""

from mvcc_system import MVCCSystem
import time


def print_separator(title=""):
    """打印分隔线"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print(f"{'='*60}\n")


def print_step(step_num, description):
    """打印步骤"""
    print(f"步骤 {step_num}: {description}")


def print_result(label, value, expected=None):
    """打印结果"""
    if expected is not None:
        status = "✓" if value == expected else "✗"
        print(f"  {status} {label}: {value} (期望: {expected})")
    else:
        print(f"  ✓ {label}: {value}")


def scenario_1_basic_visibility():
    """场景1: 基本的可见性规则"""
    print_separator("场景1: 基本的可见性规则")

    system = MVCCSystem()

    print_step(1, "事务1插入数据并提交")
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'Alice', 'age': 25})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])
    print_result("事务1已提交", f"插入行{row_id}, age=25")

    print_step(2, "事务2更新数据并提交")
    trx2 = system.begin_transaction()
    system.update_data(trx2['trx_id'], row_id, {'name': 'Alice', 'age': 26})
    system.commit_transaction(trx2['trx_id'])
    print_result("事务2已提交", "更新 age=26")

    print_step(3, "事务3更新数据但不提交")
    trx3 = system.begin_transaction()
    system.update_data(trx3['trx_id'], row_id, {'name': 'Alice', 'age': 27})
    print_result("事务3活跃", "更新 age=27 (未提交)")

    print_step(4, "事务4读取数据")
    trx4 = system.begin_transaction()
    result = system.read_data(trx4['trx_id'], row_id)
    print_result("事务4读取", f"age={result['data']['age']}", 26)
    print(f"  说明: 事务4看不到事务3的修改（未提交）")

    print_step(5, "事务3提交")
    system.commit_transaction(trx3['trx_id'])
    print_result("事务3已提交", "age=27")

    print_step(6, "事务5读取数据")
    trx5 = system.begin_transaction()
    result = system.read_data(trx5['trx_id'], row_id)
    print_result("事务5读取", f"age={result['data']['age']}", 27)
    print(f"  说明: 事务5可以看到事务3的修改（已提交）")

    print("\n💡 关键点:")
    print("  - 未提交的事务对其他事务不可见")
    print("  - 已提交的事务对新事务可见")
    print("  - ReadView 决定了数据的可见性")


def scenario_2_update_rollback():
    """场景2: UPDATE 操作的回滚"""
    print_separator("场景2: UPDATE 操作的回滚")

    system = MVCCSystem()

    print_step(1, "事务1插入数据并提交")
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'Bob', 'age': 30})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])
    print_result("事务1已提交", f"插入行{row_id}, age=30")

    print_step(2, "事务2更新数据但不提交")
    trx2 = system.begin_transaction()
    system.update_data(trx2['trx_id'], row_id, {'name': 'Bob', 'age': 31})
    print_result("事务2活跃", "更新 age=31 (未提交)")

    # 查看版本链
    row_info = system.get_row_info(row_id)
    version_count = len(row_info['version_chain']['versions'])
    print_result("版本链长度", version_count, 2)

    print_step(3, "事务2回滚")
    system.rollback_transaction(trx2['trx_id'])
    print_result("事务2已回滚", "恢复到 age=30")

    # 检查版本链
    row_info = system.get_row_info(row_id)
    version_count = len(row_info['version_chain']['versions'])
    print_result("回滚后版本链长度", version_count, 1)
    print_result("回滚后数据", f"age={row_info['row']['data']['age']}", 30)

    print_step(4, "事务3读取数据")
    trx3 = system.begin_transaction()
    result = system.read_data(trx3['trx_id'], row_id)
    print_result("事务3读取", f"age={result['data']['age']}", 30)

    print("\n💡 关键点:")
    print("  - 回滚会恢复数据到修改前的状态")
    print("  - 版本链会移除回滚的版本")
    print("  - 其他事务看到的是回滚前的数据")


def scenario_3_insert_rollback():
    """场景3: INSERT 操作的回滚"""
    print_separator("场景3: INSERT 操作的回滚")

    system = MVCCSystem()

    print_step(1, "事务1插入数据但不提交")
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'Charlie', 'age': 35})
    row_id = result['row_id']
    print_result("事务1活跃", f"插入行{row_id}, age=35 (未提交)")

    # 检查行是否存在
    row_info = system.get_row_info(row_id)
    print_result("行存在", row_info is not None, True)

    print_step(2, "事务1回滚")
    system.rollback_transaction(trx1['trx_id'])
    print_result("事务1已回滚", "删除插入的行")

    # 检查行是否被删除
    row_info = system.get_row_info(row_id)
    print_result("行存在", row_info is not None, False)

    print_step(3, "事务2尝试读取该行")
    trx2 = system.begin_transaction()
    result = system.read_data(trx2['trx_id'], row_id)
    print_result("事务2读取", result['data'], None)
    print(f"  说明: 行已被删除，无法读取")

    print("\n💡 关键点:")
    print("  - INSERT 回滚会删除插入的行")
    print("  - 版本链也会被清除")
    print("  - 其他事务无法看到该行")


def scenario_4_delete_operations():
    """场景4: DELETE 操作和可见性"""
    print_separator("场景4: DELETE 操作和可见性")

    system = MVCCSystem()

    print_step(1, "事务1插入数据并提交")
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'David', 'age': 40})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])
    print_result("事务1已提交", f"插入行{row_id}, age=40")

    print_step(2, "事务2删除数据但不提交")
    trx2 = system.begin_transaction()
    system.delete_data(trx2['trx_id'], row_id)
    print_result("事务2活跃", f"删除行{row_id} (未提交)")

    print_step(3, "事务3读取数据")
    trx3 = system.begin_transaction()
    result = system.read_data(trx3['trx_id'], row_id)
    print_result("事务3读取", f"age={result['data']['age']}", 40)
    print(f"  说明: 事务3看不到事务2的删除（未提交）")

    print_step(4, "事务2提交")
    system.commit_transaction(trx2['trx_id'])
    print_result("事务2已提交", "删除操作生效")

    print_step(5, "事务4读取数据")
    trx4 = system.begin_transaction()
    result = system.read_data(trx4['trx_id'], row_id)
    print_result("事务4读取", result['data'], None)
    print(f"  说明: 事务4看到删除后的状态（数据不可见）")

    print("\n💡 关键点:")
    print("  - DELETE 是标记删除，不是物理删除")
    print("  - 未提交的删除对其他事务不可见")
    print("  - 已提交的删除会使数据对新事务不可见")


def scenario_5_delete_rollback():
    """场景5: DELETE 操作的回滚"""
    print_separator("场景5: DELETE 操作的回滚")

    system = MVCCSystem()

    print_step(1, "事务1插入数据并提交")
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'Eve', 'age': 45})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])
    print_result("事务1已提交", f"插入行{row_id}, age=45")

    print_step(2, "事务2删除数据但不提交")
    trx2 = system.begin_transaction()
    system.delete_data(trx2['trx_id'], row_id)
    print_result("事务2活跃", f"删除行{row_id} (未提交)")

    # 检查删除标记
    row_info = system.get_row_info(row_id)
    print_result("删除标记", row_info['row']['deleted'], True)

    print_step(3, "事务2回滚")
    system.rollback_transaction(trx2['trx_id'])
    print_result("事务2已回滚", "取消删除")

    # 检查删除标记
    row_info = system.get_row_info(row_id)
    print_result("删除标记", row_info['row']['deleted'], False)
    print_result("数据恢复", f"age={row_info['row']['data']['age']}", 45)

    print_step(4, "事务3读取数据")
    trx3 = system.begin_transaction()
    result = system.read_data(trx3['trx_id'], row_id)
    print_result("事务3读取", f"age={result['data']['age']}", 45)
    print(f"  说明: 数据已恢复，可以正常读取")

    print("\n💡 关键点:")
    print("  - DELETE 回滚会取消删除标记")
    print("  - 数据恢复到删除前的状态")
    print("  - 其他事务可以正常读取数据")


def scenario_6_complex_multi_transaction():
    """场景6: 复杂的多事务场景"""
    print_separator("场景6: 复杂的多事务场景")

    system = MVCCSystem()

    print_step(1, "事务1插入数据并提交")
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'Frank', 'age': 50})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])
    print_result("事务1已提交", "插入 age=50")

    print_step(2, "事务2更新数据并提交")
    trx2 = system.begin_transaction()
    system.update_data(trx2['trx_id'], row_id, {'name': 'Frank', 'age': 51})
    system.commit_transaction(trx2['trx_id'])
    print_result("事务2已提交", "更新 age=51")

    print_step(3, "事务3更新数据并提交")
    trx3 = system.begin_transaction()
    system.update_data(trx3['trx_id'], row_id, {'name': 'Frank', 'age': 52})
    system.commit_transaction(trx3['trx_id'])
    print_result("事务3已提交", "更新 age=52")

    print_step(4, "事务4更新数据但不提交")
    trx4 = system.begin_transaction()
    system.update_data(trx4['trx_id'], row_id, {'name': 'Frank', 'age': 53})
    print_result("事务4活跃", "更新 age=53 (未提交)")

    # 查看版本链
    row_info = system.get_row_info(row_id)
    version_count = len(row_info['version_chain']['versions'])
    print_result("版本链长度", version_count, 4)

    print("\n  版本链详情:")
    for i, version in enumerate(row_info['version_chain']['versions']):
        print(f"    版本{i+1}: 事务{version['trx_id']}, age={version['data']['age']}")

    print_step(5, "事务5读取数据")
    trx5 = system.begin_transaction()
    result = system.read_data(trx5['trx_id'], row_id)
    print_result("事务5读取", f"age={result['data']['age']}", 52)
    print(f"  说明: 事务5看到事务3的版本，看不到事务4的修改")

    print_step(6, "事务4回滚")
    system.rollback_transaction(trx4['trx_id'])
    print_result("事务4已回滚", "版本链恢复")

    # 检查版本链
    row_info = system.get_row_info(row_id)
    version_count = len(row_info['version_chain']['versions'])
    print_result("回滚后版本链长度", version_count, 3)

    print_step(7, "事务6读取数据")
    trx6 = system.begin_transaction()
    result = system.read_data(trx6['trx_id'], row_id)
    print_result("事务6读取", f"age={result['data']['age']}", 52)
    print(f"  说明: 事务6仍然看到事务3的版本")

    print("\n💡 关键点:")
    print("  - 版本链记录了所有历史版本")
    print("  - 每个事务看到的数据取决于 ReadView")
    print("  - 回滚会移除未提交的版本")


def scenario_7_readview_visibility():
    """场景7: ReadView 可见性规则详解"""
    print_separator("场景7: ReadView 可见性规则详解")

    system = MVCCSystem()

    print_step(1, "事务1插入数据并提交")
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'Grace', 'age': 55})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])
    print_result("事务1已提交", "插入 age=55")

    print_step(2, "事务2更新数据并提交")
    trx2 = system.begin_transaction()
    system.update_data(trx2['trx_id'], row_id, {'name': 'Grace', 'age': 56})
    system.commit_transaction(trx2['trx_id'])
    print_result("事务2已提交", "更新 age=56")

    print_step(3, "事务3开启但不操作该行")
    trx3 = system.begin_transaction()
    print_result("事务3活跃", "未操作该行")

    print_step(4, "事务4更新数据但不提交")
    trx4 = system.begin_transaction()
    system.update_data(trx4['trx_id'], row_id, {'name': 'Grace', 'age': 57})
    print_result("事务4活跃", "更新 age=57 (未提交)")

    print_step(5, "事务5读取数据")
    trx5 = system.begin_transaction()
    print(f"\n  事务5的 ReadView:")
    print(f"    creator_trx_id: {trx5['read_view']['creator_trx_id']}")
    print(f"    m_ids: {trx5['read_view']['m_ids']}")
    print(f"    min_trx_id: {trx5['read_view']['min_trx_id']}")
    print(f"    max_trx_id: {trx5['read_view']['max_trx_id']}")

    # 验证可见性
    from transaction import ReadView
    rv = ReadView(trx5['read_view']['creator_trx_id'], trx5['read_view']['m_ids'])

    print(f"\n  可见性判断:")
    print(f"    事务1 (trx_id={trx1['trx_id']}): {rv.is_visible(trx1['trx_id'])} - 已提交，可见")
    print(f"    事务2 (trx_id={trx2['trx_id']}): {rv.is_visible(trx2['trx_id'])} - 已提交，可见")
    print(f"    事务3 (trx_id={trx3['trx_id']}): {rv.is_visible(trx3['trx_id'])} - 活跃，不可见")
    print(f"    事务4 (trx_id={trx4['trx_id']}): {rv.is_visible(trx4['trx_id'])} - 活跃，不可见")
    print(f"    事务5 (trx_id={trx5['trx_id']}): {rv.is_visible(trx5['trx_id'])} - 自己，可见")

    result = system.read_data(trx5['trx_id'], row_id)
    print_result("\n  事务5读取", f"age={result['data']['age']}", 56)
    print(f"  说明: 事务5看到事务2的版本（最后一个已提交的版本）")

    print_step(6, "事务4提交")
    system.commit_transaction(trx4['trx_id'])
    print_result("事务4已提交", "age=57")

    print_step(7, "事务6读取数据")
    trx6 = system.begin_transaction()
    result = system.read_data(trx6['trx_id'], row_id)
    print_result("事务6读取", f"age={result['data']['age']}", 57)
    print(f"  说明: 事务6可以看到事务4的修改（已提交）")

    print("\n💡 ReadView 可见性规则:")
    print("  1. trx_id == creator_trx_id → 可见（自己修改的）")
    print("  2. trx_id < min_trx_id → 可见（ReadView创建前已提交）")
    print("  3. trx_id > max_trx_id → 不可见（ReadView创建后才开始）")
    print("  4. min_trx_id ≤ trx_id ≤ max_trx_id:")
    print("     - trx_id in m_ids → 不可见（创建时还未提交）")
    print("     - trx_id not in m_ids → 可见（创建时已提交）")


def main():
    """运行所有演示场景"""
    print("\n" + "="*60)
    print("  InnoDB MVCC 可视化系统 - 演示场景")
    print("="*60)

    scenarios = [
        ("场景1: 基本的可见性规则", scenario_1_basic_visibility),
        ("场景2: UPDATE 操作的回滚", scenario_2_update_rollback),
        ("场景3: INSERT 操作的回滚", scenario_3_insert_rollback),
        ("场景4: DELETE 操作和可见性", scenario_4_delete_operations),
        ("场景5: DELETE 操作的回滚", scenario_5_delete_rollback),
        ("场景6: 复杂的多事务场景", scenario_6_complex_multi_transaction),
        ("场景7: ReadView 可见性规则详解", scenario_7_readview_visibility),
    ]

    print("\n可用的演示场景:")
    for i, (name, _) in enumerate(scenarios, 1):
        print(f"  {i}. {name}")

    print("\n选择:")
    print("  输入场景编号 (1-7) 运行单个场景")
    print("  输入 'all' 运行所有场景")
    print("  输入 'q' 退出")

    while True:
        choice = input("\n请选择: ").strip().lower()

        if choice == 'q':
            print("\n再见！")
            break
        elif choice == 'all':
            for name, func in scenarios:
                func()
                input("\n按 Enter 继续下一个场景...")
            print("\n所有场景演示完成！")
            break
        elif choice.isdigit() and 1 <= int(choice) <= len(scenarios):
            idx = int(choice) - 1
            scenarios[idx][1]()
        else:
            print("无效的选择，请重新输入")


if __name__ == '__main__':
    main()
