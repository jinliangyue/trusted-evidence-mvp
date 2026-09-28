# Trusted Evidence MVP

> 最小可信数据流转验证原型 - 回应 ISO 提案 CD v1.1 §6.5.1 七项可信数据功能

为 2026 国际标准化青年之星大赛 · 工程检测赛道 · 初赛提案配套的最小工程证据。

## 与 ISO 提案 CD v1.1 的映射

| CD v1.1 条款 | 本 MVP 实现 |
|---|---|
| §6.5.1 (a) Data Integrity | SHA-256 哈希链（prev_hash + record_hash）|
| §6.5.1 (b) Provenance | sensor_id / device_id / model_id / model_version 字段 |
| §6.5.1 (c) Authenticity | device_id 标识字段（v1 字符串；v2 路线图：数字签名）|
| §6.5.1 (d) Timestamp Verifiability | acquisition_timestamp + record_timestamp（ISO 8601 UTC 毫秒）|
| §6.5.1 (e) Auditability | operation_type + operator 字段 |
| §6.5.1 (f) Multi-party Verification | v1 占位字段；v2 路线图：签名 |
| §6.5.1 (g) Lifecycle Traceability | phase 字段（detection / evaluation / storage）|
| §7.2 Data integrity | `verify_chain()` 检测 payload + metadata 篡改 |
| §7.3 Provenance | 每次推理的完整元数据入库 |
| §7.4 Auditability | operation_type + operator 全程记录 |

## 不在本 MVP 范围内（明确声明）

- **数字签名 / PKI**：v2 路线图，签名字段已预留
- **跨链 / 联盟链**：不在学生 MVP 范围；CD v1.1 明确 technology-neutral
- **智能合约**：不在范围
- **横向多设备同步**：单机 SQLite 演示；v2 路线图

## 快速开始

```bash
# 1. 跑测试（17 项，覆盖 store / verify / bridge）
python -m pytest tests/ -v

# 2. 跑独立演示（不依赖 CNN 模型）
python demo/demo_standalone.py

# 3. 跑篡改演示（答辩现场用，最关键）
python demo/demo_tamper.py

# 4. CNN 集成演示（如 checkpoint 可用则触发真实推理，否则 mock）
python demo/demo_with_cnn.py
```

## 架构

```
[Inference Result / Inspection Event]
            |
            v
   EvidenceRecord (dataclass)
            |
            v
   EvidenceStore.append() -- 计算 prev_hash + record_hash
            |
            v
   SQLite (WAL mode)
            |
            v
   verify_chain() -- 全链两阶段校验
            |
            v
   VerificationResult (total / valid / invalid / first_invalid_sequence)
```

## 目录结构

```
trusted_evidence/
├── README.md                  本文件
├── requirements.txt           无外部依赖（仅 Python 3.9+ 标准库）
├── evidence/
│   ├── __init__.py            包导出
│   ├── schemas.py             EvidenceRecord + utc_now_iso
│   ├── store.py               EvidenceStore + compute_record_hash
│   ├── verify.py              verify_chain + tamper_for_demo
│   └── bridge.py              evidence_from_inference + store_inference
├── tests/
│   ├── __init__.py
│   ├── test_store.py          8 项：存证 + 哈希链 + 顺序
│   ├── test_verify.py         5 项：验证 + 篡改检测 + chain break
│   └── test_bridge.py         3 项：CNN 推理映射
├── demo/
│   ├── demo_standalone.py     不依赖 CNN 的纯存证演示
│   ├── demo_tamper.py         篡改检测演示（答辩现场用）
│   └── demo_with_cnn.py       CNN 推理 + 存证集成演示
└── data/                      SQLite 数据库（gitignore）
```

## 答辩现场演示流程

1. 跑 `python demo/demo_tamper.py`
2. 让评委看四阶段输出：
   - 写入 10 条推理结果 → 验证全部通过
   - 直接改 SQLite 第 5 条记录的 image_id
   - 重新验证 → 检测到 sequence 4 的 record_hash 不匹配
3. 强调这对应 CD v1.1 §6.5.1 (a) Data Integrity + §7.2 Data integrity

## 已知限制（诚实声明）

- 单机本地 SQLite，不支持分布式共识
- device_id 仅作标识，未实施加密签名
- 测试覆盖率未做正式测量（v1 演示版）
- 没有 GUI / Web 界面

## 版本

v0.1.0 - 2026-09-28 - 比赛提案配套 MVP 初版

## 关联项目

- ISO Form 04 NP v1.3: `../01-正式提交/ISO_Form_04_NP_v1.3.md`
- ISO Form 04 CD v1.1: `../01-正式提交/ISO_Form_04_CD_v1.1.md`
- CNN 裂缝检测项目（提供推理结果）: `../../项目作品/CNN裂缝检测项目/`
