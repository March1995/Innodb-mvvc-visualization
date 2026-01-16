"""
InnoDB MVCC 事务管理模块
实现事务的创建、提交、回滚等功能
"""
from typing import List, Optional, Set, Dict, Any
from datetime import datetime
from enum import Enum


class TransactionStatus(Enum):
    """事务状态"""
    ACTIVE = "active"
    COMMITTED = "committed"
    ABORTED = "aborted"


class Transaction:
    """事务类"""

    _next_trx_id = 1  # 全局事务ID计数器

    def __init__(self, isolation_level: str = "READ_COMMITTED"):
        self.trx_id = Transaction._next_trx_id
        Transaction._next_trx_id += 1
        self.status = TransactionStatus.ACTIVE
        self.isolation_level = isolation_level
        self.start_time = datetime.now()
        self.commit_time: Optional[datetime] = None
        self.read_view: Optional['ReadView'] = None
        self.operations: List[Dict[str, Any]] = []  # 操作历史
        self.modified_rows: Set[int] = set()  # 修改的数据行ID集合

    def commit(self):
        """提交事务"""
        if self.status == TransactionStatus.ACTIVE:
            self.status = TransactionStatus.COMMITTED
            self.commit_time = datetime.now()
            return True
        return False

    def rollback(self):
        """回滚事务"""
        if self.status == TransactionStatus.ACTIVE:
            self.status = TransactionStatus.ABORTED
            return True
        return False

    def is_active(self) -> bool:
        """判断事务是否活跃"""
        return self.status == TransactionStatus.ACTIVE

    def add_operation(self, op_type: str, row_id: int, details: Optional[Dict] = None):
        """记录事务执行的操作"""
        operation = {
            'type': op_type,  # 'INSERT', 'UPDATE', 'DELETE', 'READ'
            'row_id': row_id,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        self.operations.append(operation)

        # 如果是修改操作，记录修改的行ID
        if op_type in ['INSERT', 'UPDATE', 'DELETE']:
            self.modified_rows.add(row_id)

    def to_dict(self):
        """转换为字典格式"""
        return {
            'trx_id': self.trx_id,
            'status': self.status.value,
            'isolation_level': self.isolation_level,
            'start_time': self.start_time.isoformat(),
            'commit_time': self.commit_time.isoformat() if self.commit_time else None,
            'read_view': self.read_view.to_dict() if self.read_view else None,
            'operations': self.operations,
            'modified_rows': list(self.modified_rows)
        }


class ReadView:
    """
    ReadView 读视图
    用于实现MVCC的可见性判断
    """

    def __init__(self, creator_trx_id: int, active_trx_ids: List[int], max_trx_id: int):
        self.creator_trx_id = creator_trx_id  # 创建该ReadView的事务ID
        self.m_ids = sorted(active_trx_ids)  # 创建ReadView时活跃的事务ID列表
        self.min_trx_id = min(active_trx_ids) if active_trx_ids else creator_trx_id  # 最小活跃事务ID
        self.max_trx_id = max_trx_id  # 系统中下一个将要分配的事务ID
        self.create_time = datetime.now()

    def is_visible(self, trx_id: int) -> bool:
        """
        判断某个事务ID的数据版本是否对当前ReadView可见

        可见性规则：
        1. trx_id == creator_trx_id: 可见（自己修改的数据）
        2. trx_id < min_trx_id: 可见（在ReadView创建前已提交）
        3. trx_id >= max_trx_id: 不可见（在ReadView创建后才开始的事务）
        4. min_trx_id <= trx_id < max_trx_id:
           - 如果trx_id在m_ids中: 不可见（创建ReadView时还未提交）
           - 如果trx_id不在m_ids中: 可见（创建ReadView时已提交）
        """
        if trx_id == self.creator_trx_id:
            return True

        if trx_id < self.min_trx_id:
            return True

        if trx_id >= self.max_trx_id:
            return False

        return trx_id not in self.m_ids

    def to_dict(self):
        """转换为字典格式"""
        return {
            'creator_trx_id': self.creator_trx_id,
            'm_ids': self.m_ids,
            'min_trx_id': self.min_trx_id,
            'max_trx_id': self.max_trx_id,
            'create_time': self.create_time.isoformat()
        }


class TransactionManager:
    """事务管理器"""

    def __init__(self):
        self.active_transactions: List[Transaction] = []
        self.committed_transactions: List[Transaction] = []
        self.aborted_transactions: List[Transaction] = []

    def begin_transaction(self, isolation_level: str = "READ_COMMITTED") -> Transaction:
        """开启新事务"""
        trx = Transaction(isolation_level)
        self.active_transactions.append(trx)

        # 注意：根据InnoDB的实现，ReadView应该在第一次SELECT时创建，而不是在事务开启时
        # READ COMMITTED: 每次SELECT都创建新的ReadView
        # REPEATABLE READ: 第一次SELECT时创建ReadView，之后复用
        # 因此这里不再预先创建ReadView

        return trx

    def commit_transaction(self, trx_id: int) -> bool:
        """提交事务"""
        for trx in self.active_transactions:
            if trx.trx_id == trx_id:
                if trx.commit():
                    self.active_transactions.remove(trx)
                    self.committed_transactions.append(trx)
                    return True
        return False

    def rollback_transaction(self, trx_id: int) -> bool:
        """回滚事务"""
        for trx in self.active_transactions:
            if trx.trx_id == trx_id:
                if trx.rollback():
                    self.active_transactions.remove(trx)
                    self.aborted_transactions.append(trx)
                    return True
        return False

    def get_active_trx_ids(self) -> List[int]:
        """获取所有活跃事务ID"""
        return [trx.trx_id for trx in self.active_transactions]

    def get_transaction(self, trx_id: int) -> Optional[Transaction]:
        """根据ID获取事务"""
        for trx in self.active_transactions + self.committed_transactions + self.aborted_transactions:
            if trx.trx_id == trx_id:
                return trx
        return None

    def get_all_transactions(self):
        """获取所有事务"""
        return {
            'active': [trx.to_dict() for trx in self.active_transactions],
            'committed': [trx.to_dict() for trx in self.committed_transactions],
            'aborted': [trx.to_dict() for trx in self.aborted_transactions]
        }
