#!/usr/bin/env python3
"""
InnoDB MVCC 系统完整测试脚本
测试所有功能：可见性、回滚、版本链等
"""

from mvcc_system import MVCCSystem


def test_basic_visibility():
    """测试基本的可见性规则"""
    print("=" * 60)
    print("测试1: 基本可见性规则")
    print("=" * 60)

    system = MVCCSystem()

    # 事务1：插入数据
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'Alice', 'age': 25})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])
    print(f"✓ 事务{trx1['trx_id']}已提交: 插入 age=25")

    # 事务2：更新数据
    trx2 = system.begin_transaction()
    system.update_data(trx2['trx_id'], row_id, {'name': 'Alice', 'age': 26})
    system.commit_transaction(trx2['trx_id'])
    print(f"✓ 事务{trx2['trx_id']}已提交: 更新 age=26")

    # 事务3：开启但不提交
    trx3 = system.begin_transaction()
    system.update_data(trx3['trx_id'], row_id, {'name': 'Alice', 'age': 27})
    print(f"  事务{trx3['trx_id']}活跃: 更新 age=27 (未提交)")

    # 事务4：读取数据（应该看到事务2的版本）
    trx4 = system.begin_transaction()
    result = system.read_data(trx4['trx_id'], row_id)
    expected = 26
    actual = result['data']['age']
    status = "✓" if actual == expected else "✗"
    print(f"{status} 事务{trx4['trx_id']}读取: age={actual} (期望{expected})")

    # 事务3提交
    system.commit_transaction(trx3['trx_id'])
    print(f"✓ 事务{trx3['trx_id']}已提交")

    # 事务5：读取数据（应该看到事务3的版本）
    trx5 = system.begin_transaction()
    result = system.read_data(trx5['trx_id'], row_id)
    expected = 27
    actual = result['data']['age']
    status = "✓" if actual == expected else "✗"
    print(f"{status} 事务{trx5['trx_id']}读取: age={actual} (期望{expected})")

    print()
    return actual == 27


def test_update_rollback():
    """测试UPDATE操作的回滚"""
    print("=" * 60)
    print("测试2: UPDATE回滚")
    print("=" * 60)

    system = MVCCSystem()

    # 事务1：插入
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'Bob', 'age': 30})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])
    print(f"✓ 事务{trx1['trx_id']}已提交: 插入 age=30")

    # 事务2：更新但不提交
    trx2 = system.begin_transaction()
    system.update_data(trx2['trx_id'], row_id, {'name': 'Bob', 'age': 31})
    print(f"  事务{trx2['trx_id']}活跃: 更新 age=31 (未提交)")

    # 获取版本链信息
    row_info = system.get_row_info(row_id)
    version_count = len(row_info['version_chain']['versions'])
    print(f"  当前版本链长度: {version_count}")

    # 事务2回滚
    system.rollback_transaction(trx2['trx_id'])
    print(f"✓ 事务{trx2['trx_id']}已回滚")

    # 检查版本链是否正确回滚
    row_info = system.get_row_info(row_id)
    version_count = len(row_info['version_chain']['versions'])
    expected_count = 1
    status = "✓" if version_count == expected_count else "✗"
    print(f"{status} 回滚后版本链长度: {version_count} (期望{expected_count})")

    # 检查数据是否恢复
    actual_age = row_info['row']['data']['age']
    expected_age = 30
    status = "✓" if actual_age == expected_age else "✗"
    print(f"{status} 回滚后数据: age={actual_age} (期望{expected_age})")

    # 事务3：读取数据（应该看到事务1的版本）
    trx3 = system.begin_transaction()
    result = system.read_data(trx3['trx_id'], row_id)
    actual = result['data']['age']
    expected = 30
    status = "✓" if actual == expected else "✗"
    print(f"{status} 事务{trx3['trx_id']}读取: age={actual} (期望{expected})")

    print()
    return actual == 30 and version_count == 1


def test_insert_rollback():
    """测试INSERT操作的回滚"""
    print("=" * 60)
    print("测试3: INSERT回滚")
    print("=" * 60)

    system = MVCCSystem()

    # 事务1：插入但不提交
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'Charlie', 'age': 35})
    row_id = result['row_id']
    print(f"  事务{trx1['trx_id']}活跃: 插入行{row_id} (未提交)")

    # 检查行是否存在
    row_info = system.get_row_info(row_id)
    exists = row_info is not None
    status = "✓" if exists else "✗"
    print(f"{status} 插入后行存在: {exists}")

    # 事务1回滚
    system.rollback_transaction(trx1['trx_id'])
    print(f"✓ 事务{trx1['trx_id']}已回滚")

    # 检查行是否被删除
    row_info = system.get_row_info(row_id)
    exists = row_info is not None
    status = "✓" if not exists else "✗"
    print(f"{status} 回滚后行存在: {exists} (期望False)")

    print()
    return not exists


def test_delete_operations():
    """测试DELETE操作"""
    print("=" * 60)
    print("测试4: DELETE操作")
    print("=" * 60)

    system = MVCCSystem()

    # 事务1：插入数据
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'David', 'age': 40})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])
    print(f"✓ 事务{trx1['trx_id']}已提交: 插入行{row_id}, age=40")

    # 事务2：删除数据但不提交
    trx2 = system.begin_transaction()
    system.delete_data(trx2['trx_id'], row_id)
    print(f"  事务{trx2['trx_id']}活跃: 删除行{row_id} (未提交)")

    # 事务3：尝试读取（应该能看到数据）
    trx3 = system.begin_transaction()
    result = system.read_data(trx3['trx_id'], row_id)
    can_see = result['data'] is not None
    status = "✓" if can_see else "✗"
    print(f"{status} 事务{trx3['trx_id']}读取: {result['data']} (期望能看到数据)")

    # 事务2提交
    system.commit_transaction(trx2['trx_id'])
    print(f"✓ 事务{trx2['trx_id']}已提交")

    # 事务4：尝试读取（应该看不到数据）
    trx4 = system.begin_transaction()
    result = system.read_data(trx4['trx_id'], row_id)
    cannot_see = result['data'] is None
    status = "✓" if cannot_see else "✗"
    print(f"{status} 事务{trx4['trx_id']}读取: {result['data']} (期望None)")

    print()
    return can_see and cannot_see


def test_delete_rollback():
    """测试DELETE回滚"""
    print("=" * 60)
    print("测试5: DELETE回滚")
    print("=" * 60)

    system = MVCCSystem()

    # 事务1：插入数据
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'Eve', 'age': 45})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])
    print(f"✓ 事务{trx1['trx_id']}已提交: 插入行{row_id}, age=45")

    # 事务2：删除数据
    trx2 = system.begin_transaction()
    system.delete_data(trx2['trx_id'], row_id)
    print(f"  事务{trx2['trx_id']}活跃: 删除行{row_id} (未提交)")

    # 检查删除标记
    row_info = system.get_row_info(row_id)
    is_deleted = row_info['row']['deleted']
    status = "✓" if is_deleted else "✗"
    print(f"{status} 删除标记: {is_deleted} (期望True)")

    # 事务2回滚
    system.rollback_transaction(trx2['trx_id'])
    print(f"✓ 事务{trx2['trx_id']}已回滚")

    # 检查删除标记是否恢复
    row_info = system.get_row_info(row_id)
    is_deleted = row_info['row']['deleted']
    status = "✓" if not is_deleted else "✗"
    print(f"{status} 回滚后删除标记: {is_deleted} (期望False)")

    # 事务3：读取数据（应该能看到）
    trx3 = system.begin_transaction()
    result = system.read_data(trx3['trx_id'], row_id)
    actual = result['data']['age']
    expected = 45
    status = "✓" if actual == expected else "✗"
    print(f"{status} 事务{trx3['trx_id']}读取: age={actual} (期望{expected})")

    print()
    return not is_deleted and actual == 45


def test_complex_scenario():
    """测试复杂的多事务场景"""
    print("=" * 60)
    print("测试6: 复杂的多事务场景")
    print("=" * 60)

    system = MVCCSystem()

    # 事务1：插入
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'Frank', 'age': 50})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])
    print(f"✓ 事务{trx1['trx_id']}已提交: 插入 age=50")

    # 事务2：更新
    trx2 = system.begin_transaction()
    system.update_data(trx2['trx_id'], row_id, {'name': 'Frank', 'age': 51})
    system.commit_transaction(trx2['trx_id'])
    print(f"✓ 事务{trx2['trx_id']}已提交: 更新 age=51")

    # 事务3：更新
    trx3 = system.begin_transaction()
    system.update_data(trx3['trx_id'], row_id, {'name': 'Frank', 'age': 52})
    system.commit_transaction(trx3['trx_id'])
    print(f"✓ 事务{trx3['trx_id']}已提交: 更新 age=52")

    # 事务4：更新但不提交
    trx4 = system.begin_transaction()
    system.update_data(trx4['trx_id'], row_id, {'name': 'Frank', 'age': 53})
    print(f"  事务{trx4['trx_id']}活跃: 更新 age=53 (未提交)")

    # 事务5：读取（应该看到事务3的版本）
    trx5 = system.begin_transaction()
    result = system.read_data(trx5['trx_id'], row_id)
    actual = result['data']['age']
    expected = 52
    status = "✓" if actual == expected else "✗"
    print(f"{status} 事务{trx5['trx_id']}读取: age={actual} (期望{expected})")

    # 检查版本链
    row_info = system.get_row_info(row_id)
    version_count = len(row_info['version_chain']['versions'])
    print(f"  版本链长度: {version_count} (期望4)")

    # 事务4回滚
    system.rollback_transaction(trx4['trx_id'])
    print(f"✓ 事务{trx4['trx_id']}已回滚")

    # 检查版本链是否正确
    row_info = system.get_row_info(row_id)
    version_count_after = len(row_info['version_chain']['versions'])
    expected_count = 3
    status = "✓" if version_count_after == expected_count else "✗"
    print(f"{status} 回滚后版本链长度: {version_count_after} (期望{expected_count})")

    # 事务6：读取（应该仍然看到事务3的版本）
    trx6 = system.begin_transaction()
    result = system.read_data(trx6['trx_id'], row_id)
    actual = result['data']['age']
    expected = 52
    status = "✓" if actual == expected else "✗"
    print(f"{status} 事务{trx6['trx_id']}读取: age={actual} (期望{expected})")

    print()
    return actual == 52 and version_count_after == 3


def test_readview_visibility():
    """测试ReadView可见性规则"""
    print("=" * 60)
    print("测试7: ReadView可见性规则")
    print("=" * 60)

    system = MVCCSystem()

    # 事务1：插入
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'Grace', 'age': 55})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])
    print(f"✓ 事务{trx1['trx_id']}已提交: 插入 age=55")

    # 事务2：更新
    trx2 = system.begin_transaction()
    system.update_data(trx2['trx_id'], row_id, {'name': 'Grace', 'age': 56})
    system.commit_transaction(trx2['trx_id'])
    print(f"✓ 事务{trx2['trx_id']}已提交: 更新 age=56")

    # 事务3：开启但不操作该行
    trx3 = system.begin_transaction()
    print(f"  事务{trx3['trx_id']}活跃 (未操作该行)")

    # 事务4：更新但不提交
    trx4 = system.begin_transaction()
    system.update_data(trx4['trx_id'], row_id, {'name': 'Grace', 'age': 57})
    print(f"  事务{trx4['trx_id']}活跃: 更新 age=57 (未提交)")

    # 事务5：读取（应该看到事务2的版本，因为事务3、4都在活跃列表中）
    trx5 = system.begin_transaction()
    print(f"  事务{trx5['trx_id']}的ReadView: m_ids={trx5['read_view']['m_ids']}")
    result = system.read_data(trx5['trx_id'], row_id)
    actual = result['data']['age']
    expected = 56
    status = "✓" if actual == expected else "✗"
    print(f"{status} 事务{trx5['trx_id']}读取: age={actual} (期望{expected}，因为事务4未提交)")

    # 事务4提交
    system.commit_transaction(trx4['trx_id'])
    print(f"✓ 事务{trx4['trx_id']}已提交")

    # 事务6：读取（应该看到事务4的版本）
    trx6 = system.begin_transaction()
    result = system.read_data(trx6['trx_id'], row_id)
    actual = result['data']['age']
    expected = 57
    status = "✓" if actual == expected else "✗"
    print(f"{status} 事务{trx6['trx_id']}读取: age={actual} (期望{expected})")

    print()
    return actual == 57


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("InnoDB MVCC 系统完整测试")
    print("=" * 60 + "\n")

    results = []

    results.append(("基本可见性规则", test_basic_visibility()))
    results.append(("UPDATE回滚", test_update_rollback()))
    results.append(("INSERT回滚", test_insert_rollback()))
    results.append(("DELETE操作", test_delete_operations()))
    results.append(("DELETE回滚", test_delete_rollback()))
    results.append(("复杂多事务场景", test_complex_scenario()))
    results.append(("ReadView可见性规则", test_readview_visibility()))

    # 打印测试结果摘要
    print("=" * 60)
    print("测试结果摘要")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print()
    print(f"总计: {len(results)} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    print()

    if failed == 0:
        print("🎉 所有测试通过！")
    else:
        print(f"⚠️  有 {failed} 个测试失败")

    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
