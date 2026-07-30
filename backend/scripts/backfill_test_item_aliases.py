"""回填 test_items.aliases —— 把之前 SQLite 时期手动改过的别名同步到 CloudBase MySQL。

用法（本地直连线上 MySQL 或通过 API 调用）：
  方式一：直接跑（需 DATABASE_URL 环境变量可用）
    python scripts/backfill_test_item_aliases.py
  方式二：通过 API（安全）
    curl -X POST .../api/v1/_diag/backfill-aliases -H "Authorization: Bearer ..."
"""

import json
import os
import sys

# 按 test_item ID -> 补充的别名（逗号分隔，追加到现有 aliases）
# 来源：2026-07-14 apply_eqa_aliases.py + 2026-07-16 D反向 + 2026-07-28 CK-MB + 用户反馈
ALIAS_PATCHES = {
    # ====== CK-MB 系列 ======
    40: [  # 肌酸激酶同工酶
        "肌酸激酶同工酶CKMB",
        "肌酸激酶-MB 同工酶质量(CK-MBmass)",
        "肌酸激酶-MB(μg/L)",
    ],

    # ====== 2026-07-16: D反向 ======
    175: ["HAV-IgM"],                    # 甲型肝炎病毒IgM抗体
    77:  ["TP1NP"],                       # 总I型胶原氨基端延长肽
    125: ["INR"],                         # 凝血酶原时间
    188: ["血管紧张素II", "Angiotensin II"],  # 血管紧张素II
    132: ["蛋白C"],                       # 血浆蛋白C活性
    82:  ["TPAb"],                        # 梅毒特异性抗体（原 梅毒螺旋体抗体，已改名）
    208: ["TPAb"],                        # 梅毒特异性抗体（原 梅毒特异性抗体（仅孕妇），已改名）

    # ====== 2026-07-14: 38 项 EQA 短码 -> 库项目名 ======
    170: ["CMV G", "CMV M", "CMV-IgG", "CMV-IgM"],    # 巨细胞病毒
    173: ["RV G", "RV M", "RV-IgG", "RV-IgM"],         # 风疹病毒
    172: ["TOX G", "TOX M", "TOX-IgG", "TOX-IgM"],     # 弓形虫
    174: ["HSV-1/2 G", "HSV-1/2 M"],                    # 单纯疱疹病毒
    15:  ["β2微球蛋白", "B2M"],                         # β2微球蛋白
    54:  ["总T4", "TT4"],                               # 总T4
    53:  ["总T3", "TT3"],                               # 总T3
    56:  ["游离T3", "FT3"],                             # 游离T3
    55:  ["游离T4", "FT4"],                             # 游离T4
    47:  ["βHCG", "总βHCG", "β-hCG", "hCG"],           # 人绒毛膜促性腺激素
    14:  ["γ-GT", "GGT", "γ-谷氨酸氨基转移酶"],        # γ-谷氨酰转移酶
    92:  ["脂蛋白a", "Lp(a)", "脂蛋白（a）"],          # 脂蛋白a
    24:  ["抗FXa活性", "Anti-Xa"],                      # 抗FXa活性

    # ====== 2026-07-14: 快速检测胶体金别名 ======
    194: ["HIV（胶体金）", "HIV胶体金", "HIV金标", "HIV快速"],
    195: ["TP（胶体金）", "TP胶体金", "TP金标", "梅毒（胶体金）", "梅毒胶体金", "梅毒快速"],
    197: ["HCV（胶体金）", "HCV胶体金", "HCV金标", "HCV快速"],

    # ====== 用户反馈补充 ======
    27:  ["ALT", "GPT"],                  # 丙氨酸氨基转移酶（谷丙转氨酶）
    26:  ["AST", "GOT"],                  # 天门冬氨酸氨基转移酶（谷草转氨酶）
    28:  ["GGT", "γ-GT"],                # γ-谷氨酰转移酶（谷氨酰转肽酶）
    16:  ["ADA"],                         # 腺苷脱氨酶
    67:  ["直接胆红素", "DBIL"],          # 直接胆红素
    68:  ["间接胆红素", "IBIL"],          # 间接胆红素
    10:  ["LDL", "LDL-C", "LDL胆固醇"],  # 低密度脂蛋白胆固醇
    8:   ["HDL", "HDL-C", "HDL胆固醇"],  # 高密度脂蛋白胆固醇
    7:   ["TC", "CHOL", "总胆固醇"],      # 总胆固醇
    5:   ["TG", "TRIG", "甘油三脂"],     # 甘油三酯
    3:   ["TP", "总蛋白"],               # 总蛋白
    4:   ["ALB", "白蛋白"],              # 白蛋白
    17:  ["抗链O", "ASO", "抗链球菌溶血素O"],  # 抗链球菌溶血素O
    38:  ["CysC", "胱抑素C"],            # 胱抑素C
    13:  ["PFNA", "Ⅰ型前胶原氨基端原肽"],  # I型前胶原氨基端原肽
    49:  ["β-CTx", "I型胶原羧基端肽", "β-CTX"],  # I型胶原羧基端肽β特殊序列
    23:  ["hs-CRP", "超敏C反应蛋白"],    # 超敏C反应蛋白
    21:  ["CK", "CPK", "Creatine Kinase"],  # 肌酸激酶
    18:  ["RF", "类风湿因子"],            # 类风湿因子
    111: ["IgG", "免疫球蛋白G"],
    112: ["IgM", "免疫球蛋白M"],
    113: ["IgA", "免疫球蛋白A"],
    114: ["C3", "补体C3"],
    115: ["C4", "补体C4"],
    131: ["AT3", "ATIII", "抗凝血酶III"],

    # ====== 尿液/其他 ======
    139: ["尿β2微球蛋白", "尿液β2-MG"],
    140: ["尿α1微球蛋白", "尿液α1-MG"],
    141: ["尿转铁蛋白", "尿液TRF"],
    142: ["尿IgG", "尿液IgG", "尿免疫球蛋白G"],
    143: ["尿视黄醇结合蛋白", "尿液RBP"],
    144: ["尿N-乙酰-β-D-氨基葡萄糖苷酶", "尿NAG"],
}


def patch_aliases_via_api(base_url: str, token: str):
    """通过 API PATCH 逐条更新 test_items.aliases。"""
    import urllib.request

    updated = 0
    skipped = 0
    errors = []

    for tid, new_aliases in sorted(ALIAS_PATCHES.items()):
        try:
            # 先获取当前 aliases
            req = urllib.request.Request(
                f"{base_url}/api/v1/test-items/{tid}",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp = urllib.request.urlopen(req, timeout=10)
            item = json.loads(resp.read())
            current = item.get("aliases", "") or ""

            # 检查哪些别名已经存在
            existing = set(a.strip() for a in current.replace("，", ",").split(",") if a.strip())
            to_add = [a for a in new_aliases if a not in existing]
            if not to_add:
                skipped += 1
                continue

            # 合并
            merged = current.rstrip(", ") + ", " + ", ".join(to_add)

            # PATCH 更新
            payload = json.dumps({"aliases": merged}).encode("utf-8")
            req2 = urllib.request.Request(
                f"{base_url}/api/v1/test-items/{tid}",
                data=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="PATCH",
            )
            resp2 = urllib.request.urlopen(req2, timeout=10)
            updated += 1
            print(f"  ✅ id={tid} ({item.get('name','?')[:20]}) +{len(to_add)} aliases: {', '.join(to_add[:3])}")
        except Exception as e:
            errors.append(f"id={tid}: {e}")
            print(f"  ❌ id={tid}: {e}")

    print(f"\n总计: updated={updated}, skipped={skipped}, errors={len(errors)}")
    if errors:
        for e in errors[:5]:
            print(f"  ERROR: {e}")


def patch_aliases_direct(db_url: str):
    """直接连数据库 UPDATE（需 DATABASE_URL 可用且 MySQL 直连）。"""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    engine = create_engine(db_url)
    session = Session(engine)

    updated = 0
    skipped = 0
    errors = []

    for tid, new_aliases in sorted(ALIAS_PATCHES.items()):
        try:
            row = session.execute(
                text("SELECT name, aliases FROM test_items WHERE id = :id"),
                {"id": tid},
            ).fetchone()
            if not row:
                errors.append(f"id={tid}: not found")
                continue

            name, current = row[0], row[1] or ""
            existing = set(a.strip() for a in current.replace("，", ",").split(",") if a.strip())
            to_add = [a for a in new_aliases if a not in existing]
            if not to_add:
                skipped += 1
                continue

            merged = current.rstrip(", ") + ", " + ", ".join(to_add)
            session.execute(
                text("UPDATE test_items SET aliases = :aliases WHERE id = :id"),
                {"id": tid, "aliases": merged},
            )
            session.commit()
            updated += 1
            print(f"  ✅ id={tid} ({name[:20]}) +{len(to_add)} aliases")
        except Exception as e:
            session.rollback()
            errors.append(f"id={tid}: {e}")
            print(f"  ❌ id={tid}: {e}")

    session.close()
    print(f"\n总计: updated={updated}, skipped={skipped}, errors={len(errors)}")


if __name__ == "__main__":
    base_url = os.environ.get("BASE_URL", "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com")
    token = os.environ.get("API_TOKEN", "")

    if token:
        print(f"通过 API 更新 (base={base_url})")
        patch_aliases_via_api(base_url, token)
    else:
        db_url = os.environ.get("DATABASE_URL", "mysql+pymysql://labapp:Jzz6827556@10.0.1.18:3306/cloud1-0gjhamv53ff2298d")
        print(f"直接连库更新 (db={db_url[:50]}...)")
        patch_aliases_direct(db_url)
