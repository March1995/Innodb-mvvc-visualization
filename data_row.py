"""
InnoDB MVCC 数据行版本链管理模块
实现数据行的多版本管理和可见性判断
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from transaction import ReadView
from undo_log import UndoLog, UndoLogType


class DataRow:
    """数据行"""

    _next_row_id = 1

    def __init__(self, data: Dict[str, Any]):
        self.row_id = DataRow._next_row_id
        DataRow._next_row_id += 1
        self.data = data  # 当前数据
        self.trx_id: Optional[int] = None  # 最后修改该行的事务ID
        self.roll_pointer: Optional[int] = None  # 指向Undo日志的指针
        self.create_time = datetime.now()
        self.update_time = datetime.now()
        self.deleted = False  # 删除标记

    def to_dict(self):
        """转换为字典格式"""
        return {
            'row_id': self.row_id,
            'data': self.data,
            'trx_id': self.trx_id,
            'roll_pointer': self.roll_pointer,
            'create_time': self.create_time.isoformat(),
            'update_time': self.update_time.isoformat(),
            'deleted': self.deleted
        }


class VersionChain:
    """版本链 - 管理数据行的所有历史版本"""

    def __init__(self, row: DataRow):
        self.row = row
        self.versions: List[Dict[str, Any]] = []  # 历史版本列表

    def add_version(self, trx_id: int, data: Dict[str, Any], undo_id: Optional[int] = None):
        """添加新版本"""
        version = {
            'trx_id': trx_id,
            'data': data.copy(),
            'undo_id': undo_id,
            'timestamp': datetime.now().isoformat()
        }
        self.versions.append(version)

    def get_visible_version(self, read_view: ReadView, undo_logs: Dict[int, UndoLog]) -> Optional[Dict[str, Any]]:
        """
        根据ReadView获取可见的数据版本
        通过Undo日志链回溯找到第一个可见的版本

        关键理解：
        - 当前行数据是最新版本
        - Undo日志记录的是历史版本
        - 回溯时，我们需要找到第一个可见的事务，并返回该事务修改后的数据
        """
        # 检查当前版本是否可见
        if self.row.trx_id and read_view.is_visible(self.row.trx_id):
            if not self.row.deleted:
                return self.row.data.copy()
            else:
                return None  # 已删除

        # 沿着Undo链回溯，寻找第一个可见的版本
        current_undo_id = self.row.roll_pointer
        prev_undo_log = None

        while current_undo_id is not None:
            undo_log = undo_logs.get(current_undo_id)
            if undo_log is None:
                break

            # 检查该Undo日志对应的事务是否可见
            if read_view.is_visible(undo_log.trx_id):
                # 找到第一个可见的事务
                # 需要返回该事务修改后的数据

                if undo_log.log_type == UndoLogType.INSERT:
                    # INSERT操作：new_value是插入的数据
                    return undo_log.new_value.copy() if undo_log.new_value else None

                elif undo_log.log_type == UndoLogType.UPDATE:
                    # UPDATE操作：需要返回该事务修改后的数据
                    # 如果有前一个Undo日志（更新的版本），则返回前一个的old_value
                    # 否则返回当前Undo的new_value
                    if prev_undo_log and prev_undo_log.old_value:
                        return prev_undo_log.old_value.copy()
                    elif undo_log.new_value:
                        return undo_log.new_value.copy()
                    else:
                        return undo_log.old_value.copy() if undo_log.old_value else None

                elif undo_log.log_type == UndoLogType.DELETE:
                    # DELETE操作：该版本已被删除
                    return None

            # 继续回溯到更早的版本
            prev_undo_log = undo_log
            current_undo_id = undo_log.roll_pointer

        return None  # 没有可见版本

    def to_dict(self):
        """转换为字典格式"""
        return {
            'row': self.row.to_dict(),
            'versions': self.versions
        }


class DataRowManager:
    """数据行管理器"""

    def __init__(self, undo_log_manager):
        self.rows: Dict[int, DataRow] = {}  # row_id -> DataRow
        self.version_chains: Dict[int, VersionChain] = {}  # row_id -> VersionChain
        self.undo_log_manager = undo_log_manager

    def insert_row(self, trx_id: int, data: Dict[str, Any]) -> DataRow:
        """插入新行"""
        row = DataRow(data)
        row.trx_id = trx_id
        self.rows[row.row_id] = row

        # 创建版本链
        version_chain = VersionChain(row)
        version_chain.add_version(trx_id, data)
        self.version_chains[row.row_id] = version_chain

        # 创建INSERT类型的Undo日志
        undo_log = self.undo_log_manager.create_undo_log(
            UndoLogType.INSERT, trx_id, row.row_id, None, data
        )
        row.roll_pointer = undo_log.undo_id

        return row

    def update_row(self, trx_id: int, row_id: int, new_data: Dict[str, Any]) -> bool:
        """更新行"""
        if row_id not in self.rows:
            return False

        row = self.rows[row_id]
        old_data = row.data.copy()

        # 创建UPDATE类型的Undo日志
        undo_log = self.undo_log_manager.create_undo_log(
            UndoLogType.UPDATE, trx_id, row_id, old_data, new_data, row.roll_pointer
        )

        # 更新行数据
        row.data = new_data
        row.trx_id = trx_id
        row.roll_pointer = undo_log.undo_id
        row.update_time = datetime.now()

        # 添加到版本链
        if row_id in self.version_chains:
            self.version_chains[row_id].add_version(trx_id, new_data, undo_log.undo_id)

        return True

    def delete_row(self, trx_id: int, row_id: int) -> bool:
        """删除行（标记删除）"""
        if row_id not in self.rows:
            return False

        row = self.rows[row_id]
        old_data = row.data.copy()

        # 创建DELETE类型的Undo日志
        undo_log = self.undo_log_manager.create_undo_log(
            UndoLogType.DELETE, trx_id, row_id, old_data, None, row.roll_pointer
        )

        # 标记删除
        row.deleted = True
        row.trx_id = trx_id
        row.roll_pointer = undo_log.undo_id
        row.update_time = datetime.now()

        return True

    def read_row(self, row_id: int, read_view: ReadView) -> Optional[Dict[str, Any]]:
        """根据ReadView读取行数据"""
        if row_id not in self.rows:
            return None

        version_chain = self.version_chains.get(row_id)
        if version_chain is None:
            return None

        return version_chain.get_visible_version(read_view, self.undo_log_manager.undo_logs)

    def get_row(self, row_id: int) -> Optional[DataRow]:
        """获取行"""
        return self.rows.get(row_id)

    def get_all_rows(self) -> List[Dict]:
        """获取所有行"""
        return [row.to_dict() for row in self.rows.values()]

    def get_version_chain(self, row_id: int) -> Optional[Dict]:
        """获取版本链"""
        if row_id in self.version_chains:
            return self.version_chains[row_id].to_dict()
        return None

    def get_all_version_chains(self) -> Dict[int, Dict]:
        """获取所有版本链"""
        return {row_id: chain.to_dict() for row_id, chain in self.version_chains.items()}
