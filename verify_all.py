#!/usr/bin/env python3
"""
InnoDB MVCC 系统 - 完整验证脚本
验证所有改进是否正确实现
"""

import sys
from mvcc_system import MVCCSystem
from transaction import ReadView


def print_header(title):
    """打印标题"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_test(test_name, passed, details=""):
    """打印测试结果"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"     {details}")


def verify_version_chain_order():
    """验证改进1: 版本链序号 - 越新的版本序号越大"""
    print_header("验证1: 版本链序号（越新越大）")

    system = MVCCSystem()

    # 创建多个版本
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'value': 100})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])

    trx2 = system.begin_transaction()
    system.update_data(trx2['trx_id'], row_id, {'value': 200})
    system.commit_transaction(trx2['trx_id'])

    trx3 = system.begin_transaction()
    system.update_data(trx3['trx_id'], row_id, {'value': 300})
    system.commit_transaction(trx3['trx_id'])

    # 获取版本链
    row_info = system.get_row_info(row_id)
    versions = row_info['version_chain']['versions']

    # 验证：第一个版本是最旧的，最后一个版本是最新的
    oldest_value = versions[0]['data']['value']
    newest_value = versions[-1]['data']['value']

    passed = oldest_value == 100 and newest_value == 300
    print_test("版本链顺序正确", passed,
               f"最旧版本value={oldest_value}, 最新版本value={newest_value}")

    return passed


def verify_transaction_rollback():
    """验证改进2: 事务回滚功能"""
    print_header("验证2: 事务回滚功能")

    system = MVCCSystem()

    # INSERT回滚
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'value': 100})
    row_id1 = result['row_id']
    system.rollback_transaction(trx1['trx_id'])

    row_info = system.get_row_info(row_id1)
    insert_rollback_ok = row_info is None
    print_test("INSERT回滚", insert_rollback_ok, "行已被删除")

    # UPDATE回滚
    trx2 = system.begin_transaction()
    result = system.insert_data(trx2['trx_id'], {'value': 200})
    row_id2 = result['row_id']
    system.commit_transaction(trx2['trx_id'])

    trx3 = system.begin_transaction()
    system.update_data(trx3['trx_id'], row_id2, {'value': 300})

    row_info_before = system.get_row_info(row_id2)
    version_count_before = len(row_info_before['version_chain']['versions'])

    system.rollback_transaction(trx3['trx_id'])

    row_info_after = system.get_row_info(row_id2)
    version_count_after = len(row_info_after['version_chain']['versions'])
    value_after = row_info_after['row']['data']['value']

    update_rollback_ok = (version_count_before == 2 and
                          version_count_after == 1 and
                          value_after == 200)
    print_test("UPDATE回滚", update_rollback_ok,
               f"版本链从{version_count_before}个恢复到{version_count_after}个，数据恢复到{value_after}")

    # DELETE回滚
    trx4 = system.begin_transaction()
    result = system.insert_data(trx4['trx_id'], {'value': 400})
    row_id3 = result['row_id']
    system.commit_transaction(trx4['trx_id'])

    trx5 = system.begin_transaction()
    system.delete_data(trx5['trx_id'], row_id3)

    row_info_deleted = system.get_row_info(row_id3)
    is_deleted_before = row_info_deleted['row']['deleted']

    system.rollback_transaction(trx5['trx_id'])

    row_info_restored = system.get_row_info(row_id3)
    is_deleted_after = row_info_restored['row']['deleted']

    delete_rollback_ok = is_deleted_before and not is_deleted_after
    print_test("DELETE回滚", delete_rollback_ok,
               f"删除标记从{is_deleted_before}恢复到{is_deleted_after}")

    return insert_rollback_ok and update_rollback_ok and delete_rollback_ok


def verify_readview_visibility():
    """验证改进3: ReadView可见性规则"""
    print_header("验证3: ReadView可见性规则")

    system = MVCCSystem()

    # 场景：事务1、2已提交，事务3、4活跃
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'value': 100})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])

    trx2 = system.begin_transaction()
    system.update_data(trx2['trx_id'], row_id, {'value': 200})
    system.commit_transaction(trx2['trx_id'])

    trx3 = system.begin_transaction()  # 活跃但不操作该行

    trx4 = system.begin_transaction()  # 活跃并修改该行
    system.update_data(trx4['trx_id'], row_id, {'value': 300})

    trx5 = system.begin_transaction()  # 读取数据

    # 验证ReadView
    rv = ReadView(trx5['read_view']['creator_trx_id'], trx5['read_view']['m_ids'])

    can_see_trx1 = rv.is_visible(trx1['trx_id'])
    can_see_trx2 = rv.is_visible(trx2['trx_id'])
    cannot_see_trx3 = not rv.is_visible(trx3['trx_id'])
    cannot_see_trx4 = not rv.is_visible(trx4['trx_id'])

    visibility_ok = can_see_trx1 and can_see_trx2 and cannot_see_trx3 and cannot_see_trx4
    print_test("ReadView可见性判断", visibility_ok,
               f"事务1可见={can_see_trx1}, 事务2可见={can_see_trx2}, "
               f"事务3不可见={cannot_see_trx3}, 事务4不可见={cannot_see_trx4}")

    # 验证实际读取的数据
    result = system.read_data(trx5['trx_id'], row_id)
    actual_value = result['data']['value']
    expected_value = 200  # 应该看到事务2的版本

    read_correct = actual_value == expected_value
    print_test("读取正确的版本", read_correct,
               f"读取到value={actual_value}，期望value={expected_value}")

    return visibility_ok and read_correct


def verify_operation_details():
    """验证改进4: 操作详情记录"""
    print_header("验证4: 操作详情记录")

    system = MVCCSystem()

    # INSERT操作
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'name': 'Alice', 'age': 25})
    row_id = result['row_id']

    trx1_info = system.get_transaction_info(trx1['trx_id'])
    insert_op = trx1_info['operations'][0]

    insert_details_ok = (insert_op['type'] == 'INSERT' and
                         'data' in insert_op['details'] and
                         insert_op['details']['data']['name'] == 'Alice')
    print_test("INSERT操作详情", insert_details_ok,
               f"记录了插入的数据: {insert_op['details']}")

    # UPDATE操作
    system.commit_transaction(trx1['trx_id'])
    trx2 = system.begin_transaction()
    system.update_data(trx2['trx_id'], row_id, {'name': 'Alice', 'age': 26})

    trx2_info = system.get_transaction_info(trx2['trx_id'])
    update_op = trx2_info['operations'][0]

    update_details_ok = (update_op['type'] == 'UPDATE' and
                         'old_data' in update_op['details'] and
                         'new_data' in update_op['details'] and
                         update_op['details']['old_data']['age'] == 25 and
                         update_op['details']['new_data']['age'] == 26)
    print_test("UPDATE操作详情", update_details_ok,
               f"记录了旧数据和新数据: old_age={update_op['details']['old_data']['age']}, "
               f"new_age={update_op['details']['new_data']['age']}")

    # DELETE操作
    system.commit_transaction(trx2['trx_id'])
    trx3 = system.begin_transaction()
    system.delete_data(trx3['trx_id'], row_id)

    trx3_info = system.get_transaction_info(trx3['trx_id'])
    delete_op = trx3_info['operations'][0]

    delete_details_ok = (delete_op['type'] == 'DELETE' and
                         'deleted_data' in delete_op['details'] and
                         delete_op['details']['deleted_data']['name'] == 'Alice')
    print_test("DELETE操作详情", delete_details_ok,
               f"记录了被删除的数据: {delete_op['details']['deleted_data']}")

    # READ操作
    system.rollback_transaction(trx3['trx_id'])
    trx4 = system.begin_transaction()
    system.read_data(trx4['trx_id'], row_id)

    trx4_info = system.get_transaction_info(trx4['trx_id'])
    read_op = trx4_info['operations'][0]

    read_details_ok = (read_op['type'] == 'READ' and
                       'data' in read_op['details'] and
                       read_op['details']['data'] is not None)
    print_test("READ操作详情", read_details_ok,
               f"记录了读取的数据: {read_op['details']['data']}")

    return insert_details_ok and update_details_ok and delete_details_ok and read_details_ok


def verify_no_duration_field():
    """验证改进5: 移除持续时间字段"""
    print_header("验证5: 移除持续时间字段")

    system = MVCCSystem()

    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'value': 100})
    system.commit_transaction(trx1['trx_id'])

    trx1_info = system.get_transaction_info(trx1['trx_id'])

    # 验证没有duration字段
    no_duration = 'duration' not in trx1_info
    print_test("移除duration字段", no_duration,
               f"事务信息中{'没有' if no_duration else '仍有'}duration字段")

    # 验证有start_time和commit_time
    has_times = 'start_time' in trx1_info and 'commit_time' in trx1_info
    print_test("保留时间字段", has_times,
               f"有start_time和commit_time字段")

    return no_duration and has_times


def verify_complex_scenario():
    """验证改进6: 复杂场景综合测试"""
    print_header("验证6: 复杂场景综合测试")

    system = MVCCSystem()

    # 创建复杂的事务场景
    trx1 = system.begin_transaction()
    result = system.insert_data(trx1['trx_id'], {'value': 100})
    row_id = result['row_id']
    system.commit_transaction(trx1['trx_id'])

    trx2 = system.begin_transaction()
    system.update_data(trx2['trx_id'], row_id, {'value': 200})
    system.commit_transaction(trx2['trx_id'])

    trx3 = system.begin_transaction()
    system.update_data(trx3['trx_id'], row_id, {'value': 300})
    system.commit_transaction(trx3['trx_id'])

    trx4 = system.begin_transaction()
    system.update_data(trx4['trx_id'], row_id, {'value': 400})
    # 不提交

    trx5 = system.begin_transaction()
    result = system.read_data(trx5['trx_id'], row_id)

    # 验证：事务5应该看到事务3的版本（300）
    read_value = result['data']['value']
    read_correct = read_value == 300
    print_test("复杂场景读取", read_correct,
               f"事务5读取到value={read_value}，期望300（事务3的版本）")

    # 回滚事务4
    system.rollback_transaction(trx4['trx_id'])

    # 验证版本链
    row_info = system.get_row_info(row_id)
    version_count = len(row_info['version_chain']['versions'])
    version_count_correct = version_count == 3
    print_test("回滚后版本链", version_count_correct,
               f"版本链有{version_count}个版本，期望3个")

    # 验证最新数据
    current_value = row_info['row']['data']['value']
    current_value_correct = current_value == 300
    print_test("回滚后当前数据", current_value_correct,
               f"当前value={current_value}，期望300")

    return read_correct and version_count_correct and current_value_correct


def main():
    """运行所有验证"""
    print("\n" + "="*70)
    print("  InnoDB MVCC 系统 - 完整功能验证")
    print("="*70)

    results = []

    try:
        results.append(("版本链序号", verify_version_chain_order()))
        results.append(("事务回滚功能", verify_transaction_rollback()))
        results.append(("ReadView可见性", verify_readview_visibility()))
        results.append(("操作详情记录", verify_operation_details()))
        results.append(("移除持续时间", verify_no_duration_field()))
        results.append(("复杂场景测试", verify_complex_scenario()))
    except Exception as e:
        print(f"\n❌ 验证过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 打印总结
    print_header("验证结果总结")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print(f"\n总计: {total} 项验证")
    print(f"通过: {passed} 项")
    print(f"失败: {total - passed} 项")

    if passed == total:
        print("\n🎉 所有验证通过！系统功能完整且正确。")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 项验证失败，请检查。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
