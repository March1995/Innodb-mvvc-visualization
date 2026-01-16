# InnoDB MVCC 可视化系统

一个完整的InnoDB MVCC（多版本并发控制）可视化系统，完全符合InnoDB的实现规范，用于教学和演示MVCC的工作原理。

---

## ✨ 核心特性

### 1. 完全符合InnoDB规范

- ✅ **ReadView创建时机正确** - READ COMMITTED每次SELECT创建，REPEATABLE READ首次创建后复用
- ✅ **ReadView可见性判断正确** - 使用`Transaction._next_trx_id`作为max_trx_id
- ✅ **DB_ROLL_PTR语义正确** - INSERT后显示NULL，UPDATE后显示上一个版本
- ✅ **版本链完整可追溯** - 通过ROLL_PTR串联所有历史版本

### 2. Undo Log Header可视化

展示关键MVCC字段：**TRX_ID**（事务ID）、**ROLL_PTR**（回滚指针）、**ROW_ID**（行ID）、**TYPE**（操作类型）

```
╔══════════════════════════════════════════════╗
║  UPDATE          Undo Log #3                 ║
╠══════════════════════════════════════════════╣
║  TRX_ID: 3      │ ROLL_PTR: → #2            ║
║  ROW_ID: #1     │ TYPE: UPDATE              ║
╚══════════════════════════════════════════════╝
旧值: {'name': 'Alice', 'age': 26}
```

**符合InnoDB实现：**
- INSERT: 只记录主键（回滚时删除此行）
- UPDATE: 只记录旧值（回滚和MVCC使用）
- DELETE: 只记录旧值（回滚恢复使用）

### 3. 版本链可视化

- 按行ID分组展示
- 从最新到最早排序
- 使用箭头（↓）连接相邻版本
- Roll Pointer可视化（→ Undo #X）

### 4. 完整的事务管理

- 支持INSERT/UPDATE/DELETE操作
- 支持事务提交/回滚（回滚该事务的所有操作）
- INSERT回滚完全清理（数据行、版本链、Undo日志）
- 支持READ COMMITTED/REPEATABLE READ隔离级别

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install flask
```

### 2. 启动系统

```bash
python app.py
```

访问 http://127.0.0.1:5001

### 3. 基本操作

**创建版本链：**
1. 点击"开启事务"
2. 输入数据：`{"name": "Alice", "age": 25}`
3. 点击"插入"
4. 点击"提交"
5. 查看Undo Log区域的版本链

**测试回滚：**
1. 开启事务
2. 进行多次UPDATE操作
3. 点击"回滚"
4. 观察数据和版本链恢复到事务开始前的状态

---

## 📊 演示场景

### 场景1：验证READ COMMITTED

```
1. 事务1插入数据并提交
2. 事务2（READ COMMITTED）读取数据
3. 事务3更新数据并提交
4. 事务2再次读取

结果：事务2能看到事务3的更新 ✓
```

### 场景2：验证REPEATABLE READ

```
1. 事务1插入数据并提交
2. 事务2（REPEATABLE READ）读取数据
3. 事务3更新数据并提交
4. 事务2再次读取

结果：事务2看到原来的数据（不受事务3影响）✓
```

### 场景3：验证事务回滚

```
1. 开启事务
2. 进行3次UPDATE操作（age: 20→21→22→23）
3. 回滚事务

结果：
- 数据恢复到age=20 ✓
- 该事务的所有Undo日志被删除 ✓
- 版本链自动刷新 ✓
```

---

## 🏗️ 系统架构

```
Web界面 (Flask + HTML/CSS/JS)
         ↓
    MVCC System
         ↓
┌────────┴────────┐
│  事务管理        │  ReadView管理
│  数据行管理      │  Undo日志管理
│  版本链管理      │  可见性判断
└─────────────────┘
```

---

## 📁 项目结构

```
Innodb-mvvc-visualization/
├── app.py                      # Flask Web服务器
├── mvcc_system.py              # MVCC系统主逻辑
├── transaction.py              # 事务和ReadView管理
├── data_row.py                 # 数据行和版本链管理
├── undo_log.py                 # Undo日志管理
├── templates/
│   └── index.html              # HTML模板
├── static/
│   ├── js/
│   │   └── app.js              # 前端JavaScript逻辑
│   └── css/
│       └── style.css           # 样式表
└── README.md                   # 项目文档
```

---

## 🎓 学习价值

### 理解MVCC核心概念

- **多版本共存** - 通过Undo Log保存历史版本
- **ReadView可见性** - 通过TRX_ID和活跃事务列表判断
- **版本链回溯** - 通过ROLL_PTR串联历史版本
- **事务隔离** - READ COMMITTED vs REPEATABLE READ的区别

### 理解InnoDB隐藏字段

- **DB_ROW_ID** - 行ID（主键）
- **DB_TRX_ID** - 事务ID（最后修改此行的事务）
- **DB_ROLL_PTR** - 回滚指针（指向Undo Log）

### 理解Undo Log结构

- **Header** - TRX_ID、ROLL_PTR、ROW_ID、TYPE
- **Body** - 只记录旧值（新值在当前数据行中）
- **版本链** - 通过ROLL_PTR串联所有历史版本

---

## 🔧 技术实现要点

### ReadView创建时机

```python
# READ COMMITTED: 每次读取创建新ReadView
if trx.isolation_level == "READ_COMMITTED":
    current_read_view = ReadView(trx.trx_id, active_trx_ids, Transaction._next_trx_id)

# REPEATABLE READ: 第一次读取创建，之后复用
else:
    if not trx.read_view:
        trx.read_view = ReadView(trx.trx_id, active_trx_ids, Transaction._next_trx_id)
```

### 事务回滚所有操作

```python
# 收集该事务对某行的所有Undo日志
trx_undo_logs = [log for log in all_logs if log.trx_id == trx_id]

# 按undo_id降序排列（从最新到最早）
trx_undo_logs.sort(key=lambda x: x.undo_id, reverse=True)

# 逐个回滚该事务的所有操作
for undo_log in trx_undo_logs:
    # 回滚INSERT/UPDATE/DELETE操作
    ...
```

### DB_ROLL_PTR展示层转换

```python
# 内部实现：row.roll_pointer指向当前版本的Undo日志
# 展示层：display_roll_pointer显示上一个版本

if undo_log.log_type == 'INSERT':
    return None  # INSERT显示NULL
else:
    return undo_log.roll_pointer  # UPDATE/DELETE显示上一个版本
```

---

## 💡 使用技巧

1. **观察版本链形成** - 连续多次更新同一行，观察Undo Log区域版本链的增长
2. **对比隔离级别** - 两个事务同时操作，对比READ COMMITTED和REPEATABLE READ的不同行为
3. **追踪Roll Pointer** - 从最新版本一直追溯到INSERT，理解版本链回溯过程
4. **测试回滚功能** - 进行多次操作后回滚，验证所有操作都被撤销

---

## 🏆 系统特点

- ✅ **完全符合InnoDB实现** - ReadView、可见性判断、DB_ROLL_PTR语义
- ✅ **Undo Log Header可视化** - 清晰展示关键MVCC字段
- ✅ **事务回滚完整** - 回滚该事务的所有操作
- ✅ **版本链自动刷新** - 回滚后立即更新显示
- ✅ **教学友好** - 清晰的可视化效果，易于理解MVCC原理

---

## 📞 反馈

如有问题或建议，欢迎提出！

---

**版本：** 2.0.1
**最后更新：** 2026-01-16
**状态：** ✅ 生产就绪
