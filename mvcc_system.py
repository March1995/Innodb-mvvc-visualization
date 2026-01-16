"""
InnoDB MVCC 可视化系统主模块
整合所有组件，提供统一的API接口
"""
from transaction import TransactionManager, Transaction, ReadView
from undo_log import UndoLogManager
from data_row import DataRowManager
from typing import Dict, Any, List, Optional


class MVCCSystem:
    """MVCC系统主类"""

    def __init__(self):
        self.transaction_manager = TransactionManager()
        self.undo_log_manager = UndoLogManager()
        self.data_row_manager = DataRowManager(self.undo_log_manager)

    def begin_transaction(self, isolation_level: str = "READ_COMMITTED") -> Dict:
        """开启事务"""
        trx = self.transaction_manager.begin_transaction(isolation_level)
        return trx.to_dict()

    def commit_transaction(self, trx_id: int) -> Dict:
        """提交事务"""
        success = self.transaction_manager.commit_transaction(trx_id)
        return {'success': success, 'trx_id': trx_id}

    def rollback_transaction(self, trx_id: int) -> Dict:
        """回滚事务"""
        trx = self.transaction_manager.get_transaction(trx_id)
        if not trx or not trx.is_active():
            return {'success': False, 'error': 'Transaction not active'}

        # 回滚该事务的所有修改
        for row_id in trx.modified_rows:
            self._rollback_row_changes(trx_id, row_id)

        success = self.transaction_manager.rollback_transaction(trx_id)
        return {'success': success, 'trx_id': trx_id}

    def _rollback_row_changes(self, trx_id: int, row_id: int):
        """回滚某行的修改"""
        row = self.data_row_manager.get_row(row_id)
        if not row:
            return

        # 如果当前行的最后修改事务不是要回滚的事务，则不需要回滚
        if row.trx_id != trx_id:
            return

        # 通过Undo日志恢复数据
        if row.roll_pointer:
            undo_log = self.undo_log_manager.get_undo_log(row.roll_pointer)
            if undo_log:
                if undo_log.log_type.value == 'INSERT':
                    # INSERT操作回滚：完全删除该行及其版本链
                    self.data_row_manager.rows.pop(row_id, None)
                    # 完全删除版本链
                    self.data_row_manager.version_chains.pop(row_id, None)
                    # 删除该行的所有Undo日志
                    self._cleanup_undo_logs(row_id)
                elif undo_log.log_type.value == 'UPDATE':
                    # UPDATE操作回滚：恢复旧值
                    if undo_log.old_value:
                        row.data = undo_log.old_value.copy()
                        row.trx_id = undo_log.trx_id if undo_log.roll_pointer else None
                        row.roll_pointer = undo_log.roll_pointer
                        # 从版本链中移除最新版本
                        if row_id in self.data_row_manager.version_chains:
                            version_chain = self.data_row_manager.version_chains[row_id]
                            if version_chain.versions:
                                version_chain.versions.pop()
                        # 删除当前Undo日志
                        self._remove_undo_log(undo_log.undo_id)
                elif undo_log.log_type.value == 'DELETE':
                    # DELETE操作回滚：恢复删除标记
                    row.deleted = False
                    if undo_log.old_value:
                        row.data = undo_log.old_value.copy()
                    row.trx_id = undo_log.trx_id if undo_log.roll_pointer else None
                    row.roll_pointer = undo_log.roll_pointer
                    # 删除当前Undo日志
                    self._remove_undo_log(undo_log.undo_id)
        else:
            # 对于INSERT操作，roll_pointer为None的情况
            # 检查是否有INSERT类型的Undo日志
            undo_chain = self.undo_log_manager.get_undo_chain(row_id)
            if undo_chain:
                # 找到最后一个Undo日志
                last_undo = undo_chain[-1]
                if last_undo.log_type.value == 'INSERT' and last_undo.trx_id == trx_id:
                    # INSERT操作回滚：完全删除该行及其版本链
                    self.data_row_manager.rows.pop(row_id, None)
                    # 完全删除版本链
                    self.data_row_manager.version_chains.pop(row_id, None)
                    # 删除该行的所有Undo日志
                    self._cleanup_undo_logs(row_id)

    def _cleanup_undo_logs(self, row_id: int):
        """清理某行的所有Undo日志"""
        if row_id in self.undo_log_manager.row_undo_chains:
            undo_ids = self.undo_log_manager.row_undo_chains[row_id].copy()
            for undo_id in undo_ids:
                self.undo_log_manager.undo_logs.pop(undo_id, None)
            self.undo_log_manager.row_undo_chains.pop(row_id, None)

    def _remove_undo_log(self, undo_id: int):
        """删除指定的Undo日志"""
        if undo_id in self.undo_log_manager.undo_logs:
            undo_log = self.undo_log_manager.undo_logs[undo_id]
            row_id = undo_log.row_id
            # 从undo_logs中删除
            self.undo_log_manager.undo_logs.pop(undo_id, None)
            # 从row_undo_chains中删除
            if row_id in self.undo_log_manager.row_undo_chains:
                if undo_id in self.undo_log_manager.row_undo_chains[row_id]:
                    self.undo_log_manager.row_undo_chains[row_id].remove(undo_id)

    def insert_data(self, trx_id: int, data: Dict[str, Any]) -> Dict:
        """插入数据"""
        trx = self.transaction_manager.get_transaction(trx_id)
        if not trx or not trx.is_active():
            return {'success': False, 'error': 'Transaction not active'}

        row = self.data_row_manager.insert_row(trx_id, data)
        trx.add_operation('INSERT', row.row_id, {'data': data})
        return {'success': True, 'row_id': row.row_id, 'row': row.to_dict()}

    def update_data(self, trx_id: int, row_id: int, data: Dict[str, Any]) -> Dict:
        """更新数据"""
        trx = self.transaction_manager.get_transaction(trx_id)
        if not trx or not trx.is_active():
            return {'success': False, 'error': 'Transaction not active'}

        # 获取旧数据
        row = self.data_row_manager.get_row(row_id)
        old_data = row.data.copy() if row else None

        success = self.data_row_manager.update_row(trx_id, row_id, data)
        if success:
            trx.add_operation('UPDATE', row_id, {'old_data': old_data, 'new_data': data})
        return {'success': success, 'row_id': row_id}

    def delete_data(self, trx_id: int, row_id: int) -> Dict:
        """删除数据"""
        trx = self.transaction_manager.get_transaction(trx_id)
        if not trx or not trx.is_active():
            return {'success': False, 'error': 'Transaction not active'}

        # 获取被删除的数据
        row = self.data_row_manager.get_row(row_id)
        deleted_data = row.data.copy() if row else None

        success = self.data_row_manager.delete_row(trx_id, row_id)
        if success:
            trx.add_operation('DELETE', row_id, {'deleted_data': deleted_data})
        return {'success': success, 'row_id': row_id}

    def read_data(self, trx_id: int, row_id: int) -> Dict:
        """读取数据"""
        trx = self.transaction_manager.get_transaction(trx_id)
        if not trx or not trx.is_active():
            return {'success': False, 'error': 'Transaction not active'}

        # 对于READ COMMITTED隔离级别，每次读取都需要创建新的ReadView
        if trx.isolation_level == "READ_COMMITTED":
            active_trx_ids = self.transaction_manager.get_active_trx_ids()
            # 使用Transaction._next_trx_id作为max_trx_id
            from transaction import Transaction
            current_read_view = ReadView(trx.trx_id, active_trx_ids, Transaction._next_trx_id)
            data = self.data_row_manager.read_row(row_id, current_read_view)
        else:
            # 对于REPEATABLE READ，第一次读取时创建ReadView，之后复用
            if not trx.read_view:
                active_trx_ids = self.transaction_manager.get_active_trx_ids()
                from transaction import Transaction
                trx.read_view = ReadView(trx.trx_id, active_trx_ids, Transaction._next_trx_id)
            data = self.data_row_manager.read_row(row_id, trx.read_view)

        trx.add_operation('READ', row_id, {'visible': data is not None, 'data': data})
        return {'success': True, 'data': data}

    def read_data_with_path(self, trx_id: int, row_id: int) -> Dict:
        """读取数据并返回读取路径"""
        trx = self.transaction_manager.get_transaction(trx_id)
        if not trx or not trx.is_active():
            return {'success': False, 'error': 'Transaction not active'}

        # 对于READ COMMITTED隔离级别，每次读取都需要创建新的ReadView
        if trx.isolation_level == "READ_COMMITTED":
            active_trx_ids = self.transaction_manager.get_active_trx_ids()
            # 使用Transaction._next_trx_id作为max_trx_id
            from transaction import Transaction
            current_read_view = ReadView(trx.trx_id, active_trx_ids, Transaction._next_trx_id)
            data, path = self.data_row_manager.read_row_with_path(row_id, current_read_view)
        else:
            # 对于REPEATABLE READ，第一次读取时创建ReadView，之后复用
            if not trx.read_view:
                active_trx_ids = self.transaction_manager.get_active_trx_ids()
                from transaction import Transaction
                trx.read_view = ReadView(trx.trx_id, active_trx_ids, Transaction._next_trx_id)
            data, path = self.data_row_manager.read_row_with_path(row_id, trx.read_view)

        trx.add_operation('READ', row_id, {'visible': data is not None, 'data': data})
        return {'success': True, 'data': data, 'path': path}

    def get_system_state(self) -> Dict:
        """获取系统完整状态"""
        return {
            'transactions': self.transaction_manager.get_all_transactions(),
            'rows': self.data_row_manager.get_all_rows(),
            'undo_logs': self.undo_log_manager.get_all_undo_logs(),
            'version_chains': self.data_row_manager.get_all_version_chains()
        }

    def get_transaction_info(self, trx_id: int) -> Optional[Dict]:
        """获取事务详细信息"""
        trx = self.transaction_manager.get_transaction(trx_id)
        return trx.to_dict() if trx else None

    def get_row_info(self, row_id: int) -> Optional[Dict]:
        """获取数据行详细信息"""
        row = self.data_row_manager.get_row(row_id)
        if not row:
            return None

        return {
            'row': row.to_dict(),
            'version_chain': self.data_row_manager.get_version_chain(row_id),
            'undo_chain': self.undo_log_manager.get_undo_chain_dict(row_id)
        }

    def reset(self):
        """重置系统"""
        # 重置所有ID计数器
        from transaction import Transaction
        from data_row import DataRow
        from undo_log import UndoLog

        Transaction._next_trx_id = 1
        DataRow._next_row_id = 1
        UndoLog._next_undo_id = 1

        # 重新初始化系统
        self.__init__()
