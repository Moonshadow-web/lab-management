from contextlib import asynccontextmanager
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .core.config import BACKEND_DIR, FRONTEND_ORIGIN, PROJECT_ROOT, UPLOAD_ROOT
from .core.database import Base, SessionLocal, engine
from .models import *  # noqa: F401,F403 注册全部表
from .models.test_item import TestItem
from .api.v1.router import api_router
from .seed.seed import run_seed
from .services.notification_service import refresh_calibration_notifications, refresh_eqa_notifications
from .services.reminder_engine import ensure_reminder_defaults, run_reminders
from .services.comparison_report import ensure_comparison_defaults

logger = logging.getLogger("reminder")


def _migrate_schema():
    """为已存在的表补齐新增列（create_all 不会 ALTER 旧表）。

    部署时若 data/app.db 已存在旧表结构，这里补加缺失列，避免
    OperationalError: no such column。新增表由 create_all 负责创建。
    """
    alters = {
        "qc_monthly_summaries": {
            "instrument_id": "INTEGER",
            "instrument_no": "VARCHAR(100)",
        },
        "instruments": {
            "qc_instrument": "BOOLEAN",
        },
        "eqa_plans": {
            "report_file": "VARCHAR(500)",
            "result_data": "TEXT",
        },
        "users": {
            "email": "VARCHAR(120)",
            "notify_email": "BOOLEAN",
            "roles": "VARCHAR(200)",
            "must_change_password": "BOOLEAN",
            "failed_login_attempts": "INTEGER",
            "locked_until": "DATETIME",
        },
        "eqa_summaries": {
            "docx_path": "VARCHAR(500)",
            "generated_at": "TIMESTAMP",
            "category": "VARCHAR(20)",
            "department": "VARCHAR(50)",
        },
        "notify_recipients": {
            "rule_categories": "VARCHAR(200)",
        },
        "test_items": {
            "has_eqa": "INTEGER",
            "has_interlab": "INTEGER",
        },
        "interlab_items": {
            "kind": "VARCHAR(20)",
        },
        "comparison_plans": {
            "only_uncompared": "BOOLEAN",
        },
        "qc_target_batches": {
            "level": "INTEGER",
            "qc_material_id": "INTEGER",
        },
        "qc_target_results": {
            "manual": "BOOLEAN",
        },
    }
    with engine.begin() as conn:
        for table, cols in alters.items():
            try:
                res = conn.exec_driver_sql(f"PRAGMA table_info({table})")
                existing = {row[1] for row in res}
            except Exception:
                continue
            for col, ctype in cols.items():
                if col not in existing:
                    conn.exec_driver_sql(
                        f"ALTER TABLE {table} ADD COLUMN {col} {ctype}"
                    )
        # 旧总结行 category 为 NULL/空 → 回填默认「生化+凝血」，避免拆分后过滤失效
        try:
            conn.exec_driver_sql(
                "UPDATE eqa_summaries SET category='生化+凝血' "
                "WHERE category IS NULL OR category=''"
            )
        except Exception:
            pass
        # 旧总结行 department 为 NULL/空 → 回填空（拆分后查询均带 department，旧行自然成为孤儿行，可重新生成）
        try:
            conn.exec_driver_sql(
                "UPDATE eqa_summaries SET department='' WHERE department IS NULL"
            )
        except Exception:
            pass
        # 旧用户（如 admin）must_change_password 为 NULL → 置 0，避免被强制改密阻断（保留其原密码，不破坏既有脚本登录）
        try:
            conn.exec_driver_sql(
                "UPDATE users SET must_change_password=0 WHERE must_change_password IS NULL"
            )
        except Exception:
            pass
        # test_items 新增 has_eqa/has_interlab 列：旧行 NULL → 回填默认 1（默认均有室间质评/室间比对）
        try:
            conn.exec_driver_sql("UPDATE test_items SET has_eqa=1 WHERE has_eqa IS NULL")
            conn.exec_driver_sql("UPDATE test_items SET has_interlab=1 WHERE has_interlab IS NULL")
        except Exception:
            pass
        # 注意：has_eqa / has_interlab 的最终取值由下方「室间比对标记」逻辑统一计算
        #（has_eqa 由 EQA 关联自动判定，has_interlab 按「例外/有EQA/无EQA」三态设置），此处仅做 NULL 兜底。
        # interlab_items 新增 kind 列：旧行 NULL/空 → 回填默认「定量」（12 类必做项目均为定量）
        try:
            conn.exec_driver_sql(
                "UPDATE interlab_items SET kind='定量' WHERE kind IS NULL OR kind=''"
            )
        except Exception:
            pass
        # 2026-07-17：interlab_items 表结构变更——移除 our_value/ref_value（改为 InterlabLevel 表）。
        # ！！重要：此迁移「绝不删除」interlab_items / interlab_levels 表，以免部署/重启清空已录入的比对结果。
        # 采用「create_all(幂等、只建缺失表) + ALTER ADD COLUMN(补齐新列) + UPDATE(回填默认值)」的
        # 增量方式演进 schema，保证已录入数据始终安全。
        try:
            Base.metadata.create_all(bind=conn)
            res = conn.exec_driver_sql("PRAGMA table_info(interlab_items)")
            cols = {row[1] for row in res}
            if "kind" not in cols:
                conn.exec_driver_sql("ALTER TABLE interlab_items ADD COLUMN kind VARCHAR(20) NOT NULL DEFAULT '定量'")
            if "note" not in cols:
                conn.exec_driver_sql("ALTER TABLE interlab_items ADD COLUMN note VARCHAR(200) NOT NULL DEFAULT ''")
        except Exception:
            pass
        # 仪器替代关系：停用仪器不再作为任何家族成员（项目应挂在替代机而非停用机）。
        # AU5822/DXI800C/D/急诊/唐筛 已停用，由 AU5821A/B、DXI800 1-4/急/唐 取代。
        try:
            conn.exec_driver_sql(
                "DELETE FROM instrument_family_members "
                "WHERE instrument_id IN (SELECT id FROM instruments WHERE status LIKE '%停用%')"
            )
        except Exception:
            pass

    # 室间比对 / 室间质评 标记（has_eqa / has_interlab）计算较重（需遍历 215 个项目
    # 与 EQA 计划做关联匹配，且在 CFS 网络盘上偏慢），放到后台初始化（见
    # _recompute_interlab_tags），避免拖慢启动导致 CloudBase 就绪探针超时 →
    # 容器被标记异常 → 503。

    # 室内质控受控仪器白名单（月结下拉限定）：AU×3 / DXI800 1·3·4·急·唐 / 罗氏×3 /
    # TOP×3 / 血气×2 / 日立 / 东曹G8 / 爱康 / Stago(CompactMax) / 安图A6200
    QC_INSTRUMENT_IDS = [
        5, 67, 68,            # AU 生化 ×3
        69, 71, 72, 73, 74,   # DXI800 1/3/4/急/唐
        14, 15, 16,           # 罗氏 ×3
        9, 10, 11,            # TOP ×3
        13, 21,               # 血气 ×2
        12,                   # 日立 HT7600
        19,                   # 东曹 HLC-723G8
        23,                   # 爱康 URANUS
        26,                   # Stago CompactMax
        75,                   # 安图 A6200
    ]
    try:
        with SessionLocal() as db:
            from .models.instrument import Instrument
            db.query(Instrument).filter(Instrument.id.in_(QC_INSTRUMENT_IDS)).update(
                {Instrument.qc_instrument: True}, synchronize_session=False
            )
            db.commit()
    except Exception:
        pass

    # 用户邮箱字段回填：管理员账号录入默认邮箱（仅当为空时，幂等，不覆盖人工修改）；
    # 历史行 notify_email 可能为 NULL，统一回填为 1（开启邮件通知）。
    ADMIN_DEFAULT_EMAIL = "815268425@qq.com"
    try:
        with SessionLocal() as db:
            from .models.user import User

            admin = db.query(User).filter(User.username == "admin").first()
            if admin and not admin.email:
                admin.email = ADMIN_DEFAULT_EMAIL
            db.query(User).filter(User.notify_email.is_(None)).update(
                {User.notify_email: True}, synchronize_session=False
            )
            db.commit()
    except Exception:
        pass


async def _reminder_scheduler():
    """每日 08:00 自动评估规则并发送提醒（依赖 minNum>=1 的常驻实例）。"""
    while True:
        try:
            now = datetime.now()
            target = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            await asyncio.sleep((target - now).total_seconds())
            with SessionLocal() as db:
                run_reminders(db)
            logger.info("reminder scheduler run at %s", datetime.now())
        except Exception as e:  # noqa: BLE001
            logger.error("reminder scheduler error: %s", e)


def _recompute_interlab_tags(db):
    """重算 has_eqa / has_interlab（部署幂等、自修复）。较重，放后台执行。"""
    EXCLUDE_INTERLAB_NAMES = (
        '乙型肝炎病毒表面抗原定量', '可溶性生长刺激表达基因2蛋白', '抑制素B',
        '抗精子抗体IgG', '抗精子抗体IgM', '抗卵巢抗体IgG', '抗卵巢抗体IgM',
        '抗子宫内膜抗体IgG', '抗子宫内膜抗体IgM', '血管紧张素转化酶', '血氨',
        '17-羟类固醇', '17-酮类固醇', '香草扁桃酸', '肺癌自身抗体检测（七项）',
        'N-乙酰-β-D-氨基葡萄糖苷酶（尿液）',
    )
    try:
        from .api.v1.eqa_associations import _compute_associations
        for r in _compute_associations(db):
            ti = db.get(TestItem, r.id)
            if ti is None:
                continue
            ti.has_eqa = 1 if r.has_eqa else 0
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.error("recompute has_eqa failed (non-fatal): %s", e)
    try:
        with engine.begin() as conn2:
            # 有 EQA → 无室间比对
            conn2.exec_driver_sql("UPDATE test_items SET has_interlab=0 WHERE has_eqa=1")
            # 16 个例外（无 EQA 但不做室间比对）→ 无室间比对
            conn2.exec_driver_sql(
                "UPDATE test_items SET has_interlab=0 WHERE name IN (%s)"
                % ",".join("'%s'" % n for n in EXCLUDE_INTERLAB_NAMES)
            )
            # 其余无 EQA → 需做室间比对
            conn2.exec_driver_sql(
                "UPDATE test_items SET has_interlab=1 WHERE has_eqa=0 AND name NOT IN (%s)"
                % ",".join("'%s'" % n for n in EXCLUDE_INTERLAB_NAMES)
            )
    except Exception as e:  # noqa: BLE001
        logger.error("recompute has_interlab failed (non-fatal): %s", e)


async def _background_init():
    """后台初始化：重活不阻塞就绪探针，避免容器被标记异常 → 503。

    数据库已在 CFS 持久卷上保留了上一轮的数据（首次运行由镜像备份恢复），
    因此重启时这些步骤多为幂等空操作；放后台执行仅影响冷启动后极短窗口内的标签，
    不影响既有服务可用性。
    """
    try:
        with SessionLocal() as db:
            _recompute_interlab_tags(db)
            run_seed(db)
            refresh_calibration_notifications(db)
            refresh_eqa_notifications(db)
            ensure_reminder_defaults(db)
            ensure_comparison_defaults(db)
            # 质控品主数据：补齐预设（如「伯乐免疫多项」），仅当不存在时插入，幂等
            from .models.qc_material import QcMaterial as _QM
            for _pn in ["生化多项质控品", "伯乐免疫多项", "昆涞免疫多项"]:
                if not db.query(_QM).filter(_QM.name == _pn).first():
                    db.add(_QM(name=_pn, items_json="[]"))
            db.commit()
            # 升级兼容：已有接收人若未配置订阅分类，默认订阅全部现有规则
            from .models.reminder import NotifyRecipient as _NR, ReminderRule as _RR
            _cats = [r.category for r in db.query(_RR).all() if r.category]
            if _cats:
                _csv = ",".join(_cats)
                for _rec in db.query(_NR).filter(
                    (_NR.rule_categories.is_(None)) | (_NR.rule_categories == "")
                ).all():
                    _rec.rule_categories = _csv
                db.commit()
            run_reminders(db)
    except Exception as e:  # noqa: BLE001
        logger.error("background init error (non-fatal, skipped): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 同步、轻量初始化：建表 + 迁移补列（快，不阻塞就绪探针）
    try:
        Base.metadata.create_all(bind=engine)
        _migrate_schema()
    except Exception as e:  # noqa: BLE001
        logger.error("init error (create_all/migrate): %s", e)
    # 重活放后台：关联打标 / 种子 / 刷新通知 / 提醒，避免启动过慢导致探针超时
    asyncio.create_task(_background_init())
    asyncio.create_task(_reminder_scheduler())
    yield


app = FastAPI(title="检验科生免组实验室管理系统", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# gzip 压缩响应体（含前端静态资源），减小公网传输体积，缓解首屏“有的慢”
app.add_middleware(GZipMiddleware, minimum_size=500)


# 带内容 hash 的前端 assets（/assets/*）设永久缓存：
# 文件名随内容变化，内容变则 hash 变、URL 变，浏览器可安全长期缓存，
# 避免每次打开/刷新都重新下载大 JS/CSS（这也是本地开发快、线上“有的慢”的主因）。
class AssetCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


app.add_middleware(AssetCacheMiddleware)

app.include_router(api_router)

# 本地磁盘文件预览（上云由云存储 SDK 的临时 URL 替代）
if UPLOAD_ROOT.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")


@app.get("/health")
def health():
    return {"status": "ok"}


# ====== 生产模式：托管前端 SPA ======
# 当 frontend/dist 存在时（Docker 构建产物），FastAPI 直接 serve 前端，
# 不需要额外的 nginx 或静态托管。同源部署，无 CORS 问题。
# 兼容本地开发（PROJECT_ROOT/frontend/dist）和 Docker（BACKEND_DIR/frontend/dist）
import os as _os
_FRONTEND_DIST = None
for _candidate in [
    _os.getenv("FRONTEND_DIST"),
    str(PROJECT_ROOT / "frontend" / "dist"),
    str(BACKEND_DIR / "frontend" / "dist"),
]:
    if _candidate and Path(_candidate).exists():
        _FRONTEND_DIST = Path(_candidate)
        break
if _FRONTEND_DIST:
    from fastapi.responses import FileResponse

    # 静态资源（JS/CSS/图片等）
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    # SPA fallback：所有非 /api、/uploads、/health 的请求都返回 index.html
    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        # 排除 API 和上传路径（已被上面的路由/挂载处理）
        if full_path.startswith(("api/", "uploads/", "health")):
            raise HTTPException(status_code=404, detail="Not found")
        index = _FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(str(index))
        raise HTTPException(status_code=404, detail="Frontend not built")
