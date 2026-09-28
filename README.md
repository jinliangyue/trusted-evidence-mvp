# Trusted Evidence MVP

> 最小可信数据流转验证原型 - 回应 ISO 提案 CD v1.1 §6.5.1 七项可信数据功能

为 2026 国际标准化青年之星大赛 · 工程检测赛道 · 初赛提案配套的最小工程证据。

**当前版本：v0.2** · HMAC-SHA256 多方签名 + 性能基准

---

## 与 ISO 提案 CD v1.1 的映射

| CD v1.1 条款 | 本 MVP 实现 | 版本 |
|---|---|---|
| §6.5.1 (a) Data Integrity | SHA-256 哈希链（prev_hash + record_hash）| v0.1 |
| §6.5.1 (b) Provenance | sensor_id / device_id / model_id / model_version 字段 | v0.1 |
| §6.5.1 (c) Authenticity | HMAC-SHA256 签名 + signer_id | v0.2 |
| §6.5.1 (d) Timestamp Verifiability | acquisition_timestamp + record_timestamp（ISO 8601 UTC 毫秒）| v0.1 |
| §6.5.1 (e) Auditability | operation_type + operator 字段 | v0.1 |
| §6.5.1 (f) Multi-party Verification | 多方各自 secret + 派生 signer_id | v0.2 |
| §6.5.1 (g) Lifecycle Traceability | phase 字段（detection / evaluation / storage）| v0.1 |
| §7.2 Data integrity | `verify_chain()` 检测 payload + metadata 篡改 | v0.1 |
| §7.3 Provenance | 每次推理的完整元数据入库 | v0.1 |
| §7.4 Auditability | operation_type + operator 全程记录 | v0.1 |
| §6.5.3 实现层性能报告 | `scripts/benchmark.py` 提供基线数字 | v0.2 |

## 快速开始

```bash
# 1. 跑测试（27 项，覆盖 store / verify / bridge / signatures）
python3 -m pytest tests/ -v

# 2. 跑独立演示（不依赖 CNN 模型）
python3 demo/demo_standalone.py

# 3. 跑篡改演示（答辩现场用，最关键）
python3 demo/demo_tamper.py

# 4. 跑签名演示（v0.2 新增，多方签名场景）
python3 demo/demo_signatures.py

# 5. CNN 集成演示（如 checkpoint 可用则触发真实推理，否则 mock）
python3 demo/demo_with_cnn.py

# 6. 跑性能基准（CD v1.1 §6.5.3 合规性证据）
python3 scripts/benchmark.py
```

## 架构

```
[Inference Result / Inspection Event]
            |
            v
   EvidenceRecord (dataclass) + optional (signer_id, signature)
            |
            v
   EvidenceStore.append() -- 计算 prev_hash + record_hash
            |
            v
   SQLite (WAL mode)
            |
            v
   verify_chain(signature_secret=None|bytes)
     - hash chain integrity check
     - optional signature verification
            |
            v
   VerificationResult (total / valid / invalid / signature_checked)
```

## 目录结构

```
trusted_evidence/
├── README.md                  本文件
├── requirements.txt           无外部依赖（仅 Python 3.9+ 标准库）
├── conftest.py
├── evidence/
│   ├── __init__.py            包导出（v0.2 含 5 个签名 API）
│   ├── schemas.py             EvidenceRecord（含可选 signature 字段）
│   ├── store.py               EvidenceStore + compute_record_hash
│   ├── verify.py              verify_chain(signature_secret=None)
│   ├── bridge.py              evidence_from_inference + store_inference
│   └── signatures.py          HMAC-SHA256 sign/verify + signer_id 派生
├── tests/
│   ├── __init__.py
│   ├── test_store.py          8 项：存证 + 哈希链 + 顺序
│   ├── test_verify.py         5 项：验证 + 篡改检测 + chain break
│   ├── test_bridge.py         3 项：CNN 推理映射
│   └── test_signatures.py     11 项：HMAC 签名 + 多方 + 向后兼容
├── demo/
│   ├── demo_standalone.py     不依赖 CNN 的纯存证演示
│   ├── demo_tamper.py         篡改检测演示（答辩现场用）
│   ├── demo_with_cnn.py       CNN 推理 + 存证集成演示
│   └── demo_signatures.py     多方签名演示（v0.2 新增）
├── scripts/
│   └── benchmark.py           性能基准（v0.2 新增 · CD §6.5.3 合规性）
└── data/                      SQLite 数据库（gitignore）
```

## 版本演进

### v0.2 (2026-09-28)

**新增**：
- `evidence/signatures.py` - HMAC-SHA256 签名 / 验证 / signer_id 派生
- `tests/test_signatures.py` - 11 项测试覆盖签名
- `demo/demo_signatures.py` - 多方签名演示
- `scripts/benchmark.py` - 性能基准（响应 CD §6.5.3 实现层性能报告要求）

**修改**：
- `EvidenceRecord` 增加可选 `signer_id` + `signature` 字段
- `EvidenceStore` schema 增加对应列
- `verify_chain()` 增加 `signature_secret` 可选参数
- 全部向后兼容：v0.1 记录无 signature 字段，验证时跳过签名检查

**实现选择说明**：
- **HMAC-SHA256** 而不是完整 PKI：学生 MVP 范围，避免引入 cryptography 外部依赖
- v0.3 路线图：Ed25519 / ECDSA / SM2 非对称签名，支持 true PKI

### v0.1 (2026-09-28 初次发布)

- 17 文件 · 16 测试 · 3 demo · CI passing
- GitHub: https://github.com/jinliangyue/trusted-evidence-mvp

## 答辩现场演示流程（v0.2 升级版）

1. 跑 `python3 demo/demo_tamper.py`：四阶段输出（写入 → 验证通过 → 篡改 → 验证失败）
2. 跑 `python3 demo/demo_signatures.py`：展示 3 方签名 + 篡改后签名失败
3. 跑 `python3 scripts/benchmark.py`：展示 1000 条记录的吞吐量数字
4. 打开 `Annex_F_应用案例集_v1.0.md` 看 3 个应用案例
5. 打开 `Annex_G_与现有标准映射矩阵_v1.0.md` 看与现有标准的关系

## 已知限制（诚实声明）

- 单机本地 SQLite，不支持分布式共识
- HMAC 是对称密钥，不是 true PKI（v0.3 路线图）
- 测试覆盖率未做正式测量（v1 演示版）
- 没有 GUI / Web 界面
- 性能基准未做多机 / 网络 / 并发测试

## 关联项目

- ISO Form 04 NP v1.3: `../提交包/01-正式提交/ISO_Form_04_NP_v1.3.md`
- ISO Form 04 CD v1.1: `../提交包/01-正式提交/ISO_Form_04_CD_v1.1.md`
- Annex F 应用案例集: `../提交包/02-答辩备用/Annex_F_应用案例集_v1.0.md`
- Annex G 与现有标准映射: `../提交包/02-答辩备用/Annex_G_与现有标准映射矩阵_v1.0.md`
- CNN 裂缝检测项目（提供推理结果）: `../../项目作品/CNN裂缝检测项目/`
