# InnoDB MVCC 可视化系统

一个用于演示和学习 InnoDB 多版本并发控制（MVCC）机制的可视化系统。

## 功能特性

- **事务管理**: 支持开启、提交、回滚事务
- **隔离级别**: 支持 READ COMMITTED 和 REPEATABLE READ 隔离级别
- **ReadView 可视化**: 实时展示事务的 ReadView 视图
- **Undo Log 展示**: 完整展示 Undo 日志链
- **版本链可视化**: 直观展示数据行的多版本链
- **数据操作**: 支持插入、更新、删除、读取操作
- **实时更新**: 自动刷新系统状态

## 系统架构

```
├── transaction.py      # 事务管理模块
├── undo_log.py        # Undo日志管理模块
├── data_row.py        # 数据行版本链管理模块
├── mvcc_system.py     # MVCC系统主模块
├── app.py             # Flask Web服务器
├── templates/         # HTML模板
│   └── index.html
└── static/            # 静态资源
    ├── css/
    │   └── style.css
    └── js/
        └── app.js
```

## 安装和运行

### 1. 使用 pyenv 创建虚拟环境

```bash
# 设置项目使用的 Python 版本（例如 3.11.0）
pyenv local 3.11.0

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行应用

```bash
python app.py
```

### 4. 访问系统

打开浏览器访问: http://localhost:5000

## 使用说明

### 基本操作流程

1. **开启事务**: 选择隔离级别，点击"开启新事务"按钮
2. **插入数据**: 输入事务ID和JSON格式的数据，点击"插入"
3. **更新数据**: 输入事务ID、行ID和新数据，点击"更新"
4. **读取数据**: 输入事务ID和行ID，点击"读取"查看可见版本
5. **提交/回滚**: 在活跃事务列表中点击相应按钮

### 示例场景

#### 场景1: 演示 READ COMMITTED 隔离级别

```
1. 开启事务1 (READ_COMMITTED)
2. 事务1插入数据: {"name": "张三", "age": 25}
3. 开启事务2 (READ_COMMITTED)
4. 事务2读取数据 -> 看不到事务1的数据
5. 提交事务1
6. 事务2再次读取 -> 可以看到事务1的数据（不可重复读）
```

#### 场景2: 演示 REPEATABLE READ 隔离级别

```
1. 开启事务1 (REPEATABLE_READ)
2. 事务1插入数据: {"name": "李四", "age": 30}
3. 开启事务2 (REPEATABLE_READ)
4. 事务2读取数据 -> 看不到事务1的数据
5. 提交事务1
6. 事务2再次读取 -> 仍然看不到事务1的数据（可重复读）
```

#### 场景3: 演示版本链和 Undo Log

```
1. 开启事务1，插入数据: {"name": "王五", "salary": 5000}
2. 提交事务1
3. 开启事务2，更新数据: {"name": "王五", "salary": 6000}
4. 开启事务3，更新数据: {"name": "王五", "salary": 7000}
5. 点击数据行查看版本链，可以看到完整的历史版本
6. 查看 Undo Log 面板，可以看到所有的 Undo 日志记录
```

## MVCC 核心概念

### ReadView

ReadView 是事务在某个时刻对数据库的快照视图，包含：
- `creator_trx_id`: 创建该 ReadView 的事务ID
- `m_ids`: 创建 ReadView 时活跃的事务ID列表
- `min_trx_id`: 最小活跃事务ID
- `max_trx_id`: 最大活跃事务ID

### 可见性判断规则

1. `trx_id == creator_trx_id`: 可见（自己修改的数据）
2. `trx_id < min_trx_id`: 可见（在 ReadView 创建前已提交）
3. `trx_id > max_trx_id`: 不可见（在 ReadView 创建后才开始）
4. `min_trx_id <= trx_id <= max_trx_id`:
   - 如果 `trx_id` 在 `m_ids` 中: 不可见（创建 ReadView 时还未提交）
   - 如果 `trx_id` 不在 `m_ids` 中: 可见（创建 ReadView 时已提交）

### Undo Log

Undo Log 记录了数据的历史版本，用于：
- 事务回滚
- MVCC 版本链回溯
- 实现一致性读

每条 Undo Log 包含：
- `log_type`: 日志类型（INSERT/UPDATE/DELETE）
- `trx_id`: 创建该日志的事务ID
- `old_value`: 旧值
- `new_value`: 新值
- `roll_pointer`: 指向上一个版本的指针

### 版本链

每个数据行维护一个版本链，通过 `roll_pointer` 连接所有历史版本。
读取数据时，沿着版本链回溯，找到第一个对当前 ReadView 可见的版本。

## API 接口

### 事务相关

- `POST /api/transaction/begin` - 开启事务
- `POST /api/transaction/commit` - 提交事务
- `POST /api/transaction/rollback` - 回滚事务
- `GET /api/transaction/<trx_id>` - 获取事务信息

### 数据操作

- `POST /api/data/insert` - 插入数据
- `POST /api/data/update` - 更新数据
- `POST /api/data/delete` - 删除数据
- `POST /api/data/read` - 读取数据

### 系统状态

- `GET /api/system/state` - 获取系统完整状态
- `POST /api/system/reset` - 重置系统
- `GET /api/row/<row_id>` - 获取数据行详细信息

## 技术栈

- **后端**: Python 3.11+ / Flask
- **前端**: HTML5 / CSS3 / JavaScript (Vanilla)
- **架构**: RESTful API

## 注意事项

1. 这是一个教学演示系统，简化了 InnoDB 的实际实现
2. 未实现真正的持久化存储
3. 未实现锁机制
4. 未实现完整的事务隔离级别（如 SERIALIZABLE）
5. 仅用于学习和理解 MVCC 原理

## 学习资源

- [MySQL InnoDB 官方文档](https://dev.mysql.com/doc/refman/8.0/en/innodb-storage-engine.html)
- [InnoDB MVCC 原理详解](https://dev.mysql.com/doc/refman/8.0/en/innodb-multi-versioning.html)

## 许可证

MIT License
