"""
InnoDB MVCC UndoLog 日志管理模块
实现Undo日志链的创建和管理
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class UndoLogType(Enum):
    """Undo日志类型"""
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class UndoLog:
    """Undo日志记录"""

    _next_undo_id = 1

    def __init__(self, log_type: UndoLogType, trx_id: int, row_id: int,
                 old_value: Optional[Dict[str, Any]] = None,
                 new_value: Optional[Dict[str, Any]] = None):
        self.undo_id = UndoLog._next_undo_id
        UndoLog._next_undo_id += 1
        self.log_type = log_type
        self.trx_id = trx_id  # 创建该Undo日志的事务ID
        self.row_id = row_id  # 关联的数据行ID
        self.old_value = old_value  # 旧值
        self.new_value = new_value  # 新值
        self.create_time = datetime.now()
        self.roll_pointer: Optional[int] = None  # 指向上一个版本的Undo日志ID

    def to_dict(self):
        """转换为字典格式"""
        return {
            'undo_id': self.undo_id,
            'log_type': self.log_type.value,
            'trx_id': self.trx_id,
            'row_id': self.row_id,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'create_time': self.create_time.isoformat(),
            'roll_pointer': self.roll_pointer
        }


class UndoLogManager:
    """Undo日志管理器"""

    def __init__(self):
        self.undo_logs: Dict[int, UndoLog] = {}  # undo_id -> UndoLog
        self.row_undo_chains: Dict[int, List[int]] = {}  # row_id -> [undo_id列表]

    def create_undo_log(self, log_type: UndoLogType, trx_id: int, row_id: int,
                       old_value: Optional[Dict[str, Any]] = None,
                       new_value: Optional[Dict[str, Any]] = None,
                       prev_undo_id: Optional[int] = None) -> UndoLog:
        """创建Undo日志"""
        undo_log = UndoLog(log_type, trx_id, row_id, old_value, new_value)

        # 设置roll_pointer指向上一个版本
        if prev_undo_id is not None:
            undo_log.roll_pointer = prev_undo_id

        self.undo_logs[undo_log.undo_id] = undo_log

        # 维护行的Undo链
        if row_id not in self.row_undo_chains:
            self.row_undo_chains[row_id] = []
        self.row_undo_chains[row_id].append(undo_log.undo_id)

        return undo_log

    def get_undo_log(self, undo_id: int) -> Optional[UndoLog]:
        """获取Undo日志"""
        return self.undo_logs.get(undo_id)

    def get_undo_chain(self, row_id: int) -> List[UndoLog]:
        """获取某行的完整Undo链"""
        if row_id not in self.row_undo_chains:
            return []

        undo_ids = self.row_undo_chains[row_id]
        return [self.undo_logs[undo_id] for undo_id in undo_ids if undo_id in self.undo_logs]

    def get_all_undo_logs(self) -> List[Dict]:
        """获取所有Undo日志"""
        return [undo.to_dict() for undo in self.undo_logs.values()]

    def get_undo_chain_dict(self, row_id: int) -> List[Dict]:
        """获取某行的Undo链（字典格式）"""
        chain = self.get_undo_chain(row_id)
        return [undo.to_dict() for undo in chain]
