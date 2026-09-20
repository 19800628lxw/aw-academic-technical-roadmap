#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学术技术路线图生成器 v2.0 — 从结构化 JSON 生成 drawio 可渲染 mxgraph XML。

用法:
    python gen_roadmap.py --spec spec.json --output roadmap.drawio

支持三种范式:
    five-stage    纵向递进五段式(A4竖版, 阶段虚线框+右侧研究方法栏)
    three-column  三栏并行式(A4横版, 研究框架|研究内容|研究方法)
    loop          逻辑闭环式(圆环布局, 含反馈虚线)

spec.json 格式见 references/spec-example.json。
所有版式参数内置自 references/design-system.md, 无需手工调参。
"""
import argparse
import json
import math
import sys
from xml.sax.saxutils import escape

# ---- 设计系统令牌 (design-system.md §5/§6) ----
INK, BODY, STAGE, MUTE, WASH, PAPER = ("#000000", "#333333", "#666666",
                                       "#999999", "#F5F5F5", "#FFFFFF")
S_TITLE = (f"rounded=0;whiteSpace=wrap;html=1;fillColor={PAPER};strokeColor={INK};"
           "fontSize=15;fontStyle=1")
S_STAGE = (f"rounded=0;whiteSpace=wrap;html=1;dashed=1;fillColor=none;strokeColor={STAGE};"
           "verticalAlign=top;fontSize=13;fontStyle=1;spacingTop=4")
S_BOX = (f"rounded=0;whiteSpace=wrap;html=1;fillColor={PAPER};strokeColor={BODY};"
         "fontSize=11")
S_CONCL = (f"rounded=0;whiteSpace=wrap;html=1;fillColor={PAPER};strokeColor={INK};"
           "fontSize=13;fontStyle=1")
S_METHOD = (f"rounded=0;whiteSpace=wrap;html=1;fillColor={WASH};strokeColor={STAGE};"
            "fontSize=11;align=left;spacingLeft=8")
S_CENTER = (f"ellipse;whiteSpace=wrap;html=1;fillColor=none;strokeColor={STAGE};"
            "dashed=1;fontSize=14;fontStyle=1")
S_EDGE_V = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=" + INK +
            ";exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0")
S_EDGE_H = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=" + INK +
            ";exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0")
S_EDGE_DASH = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;dashed=1;strokeColor=" + MUTE)
S_EDGE_LOOP = "edgeStyle=none;rounded=1;curved=1;html=1;strokeColor=" + INK
S_EDGE_FEED = "edgeStyle=none;rounded=1;curved=1;html=1;dashed=1;strokeColor=" + MUTE

BOX_H, BOX_MAX_W, H_PAD, H_GAP, ROW_GAP = 60, 150, 8, 15, 12
STAGE_GAP = 40
HEAD_H, BOTTOM_PAD = 45, 20


def v(value):
    """转义文本并把换行转为 drawio 软换行。"""
    return escape(value).replace("\n", "&#10;")


def cell(cid, value, style, x, y, w, h, parent="1"):
    return (f'        <mxCell id="{cid}" value="{v(value)}" style="{style}" '
            f'vertex="1" parent="{parent}">\n'
            f'          <mxGeometry x="{round(x, 1)}" y="{round(y, 1)}" '
            f'width="{round(w, 1)}" height="{round(h, 1)}" as="geometry" />\n'
            f'        </mxCell>')


def edge(eid, src, dst, style, label=""):
    lv = f' value="{v(label)}"' if label else ""
    return (f'        <mxCell id="{eid}"{lv} style="{style}" edge="1" parent="1" '
            f'source="{src}" target="{dst}">\n'
            f'          <mxGeometry relative="1" as="geometry" />\n'
            f'        </mxCell>')


def wrap_xml(name, pw, ph, body):
    return f'''<mxfile host="app.diagrams.net">
  <diagram name="{escape(name)}" id="roadmap-gen">
    <mxGraphModel dx="1420" dy="820" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{pw}" pageHeight="{ph}" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
{body}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
'''


def _rows(items, per=4):
    return [items[i:i + per] for i in range(0, len(items), per)]


# ---------- 范式一: 纵向递进五段式 ----------
def gen_five(spec):
    cells, edges = [], []
    y = 40
    chain = []

    if spec.get("title"):
        cells.append(cell("title", spec["title"], S_TITLE, 160, y, 360, 50))
        chain.append("title")
        y += 50 + STAGE_GAP

    stage_ids, stage_geo = [], []
    for i, st in enumerate(spec["stages"], 1):
        sid = f"s{i}"
        items = st.get("items", [])
        rows = _rows(items)
        h = HEAD_H + len(rows) * BOX_H + (len(rows) - 1) * ROW_GAP + BOTTOM_PAD
        cells.append(cell(sid, st.get("name", f"阶段{i}"), S_STAGE, 60, y, 560, h))
        ry = y + HEAD_H
        for row in rows:
            n = len(row)
            bw = min(BOX_MAX_W, (560 - 2 * H_PAD - (n - 1) * H_GAP) / n)
            total = n * bw + (n - 1) * H_GAP
            bx = 60 + (560 - total) / 2
            for k, it in enumerate(row):
                cells.append(cell(f"s{i}_{k}", it, S_BOX, bx, ry, bw, BOX_H, parent=sid))
                bx += bw + H_GAP
            ry += BOX_H + ROW_GAP
        stage_ids.append(sid)
        stage_geo.append((sid, y, h))
        y += h + STAGE_GAP

    if spec.get("conclusion"):
        cells.append(cell("concl", spec["conclusion"], S_CONCL, 160, y, 360, 50))
        chain.append("concl")

    chain = ([c for c in chain if c == "title"] + stage_ids +
             [c for c in chain if c == "concl"])
    for a, b in zip(chain, chain[1:]):
        edges.append(edge(f"e_{a}_{b}", a, b, S_EDGE_V))

    methods = spec.get("methods", [])
    if methods:
        top = stage_geo[0][1]
        bottom = stage_geo[-1][1] + stage_geo[-1][2]
        mh = bottom - top
        cells.append(cell("methods", "研究方法\n\n" + "\n".join("· " + m for m in methods),
                          S_METHOD, 660, top, 120, mh))
        for j, (sid, sy, sh) in enumerate(stage_geo, 1):
            exit_y = round(((sy + sh / 2) - top) / mh, 2)
            edges.append(edge(
                f"me{j}", "methods", sid,
                S_EDGE_DASH + f";exitX=0;exitY={exit_y};exitDx=0;exitDy=0"
                ";entryX=1;entryY=0.5;entryDx=0;entryDy=0"))
    return wrap_xml("技术路线图-纵向递进五段式", 827, 1169, "\n".join(cells + edges))


# ---------- 范式二: N 栏并行式(三栏/五栏通用) ----------
def gen_columns(spec, n_cols=None):
    cells, edges = [], []
    cols = spec["columns"]
    if n_cols:
        cols = (cols + [{"name": f"栏目{i}", "items": []} for i in range(len(cols) + 1, n_cols + 1)])[:n_cols]
    n = len(cols)
    margin, col_gap, col_y = 40, 20, 110
    page_w = 1169 if n >= 3 else 827
    col_w = min(350, (page_w - 2 * margin - (n - 1) * col_gap) / n)
    xs = [margin + i * (col_w + col_gap) for i in range(n)]
    item_h, item_gap, head_h = 50, 14, 50

    heights = [head_h + len(c["items"]) * item_h + max(0, len(c["items"]) - 1) * item_gap + 16
               for c in cols]
    H = max(heights)

    if spec.get("title"):
        cells.append(cell("title", spec["title"], S_TITLE, (page_w - 500) / 2, 30, 500, 50))

    ids = []
    for i, (c, x) in enumerate(zip(cols, xs), 1):
        cid = f"c{i}"
        ids.append(cid)
        cells.append(cell(cid, c["name"], S_STAGE, x, col_y, col_w, H))
        bw = col_w - 24
        for j, it in enumerate(c.get("items", [])):
            cells.append(cell(f"c{i}_{j}", it, S_BOX, 12, head_h + j * (item_h + item_gap),
                              bw, item_h, parent=cid))
    for a, b in zip(ids, ids[1:]):
        edges.append(edge(f"e_{a}_{b}", a, b, S_EDGE_H))
    return wrap_xml(f"技术路线图-{n}栏并行式", page_w, 827, "\n".join(cells + edges))


# ---------- 范式三: 逻辑闭环式 ----------
def gen_loop(spec):
    cells, edges = [], []
    nodes = spec["stages"]
    n = len(nodes)
    if n < 3:
        sys.exit("loop 范式至少需要 3 个节点")
    cx, cy, R, bw, bh = 413, 580, 240, 180, 80

    if spec.get("title"):
        cells.append(cell("title", spec["title"], S_TITLE, (827 - 400) / 2, 40, 400, 50))
    if spec.get("center"):
        cells.append(cell("center", spec["center"], S_CENTER, cx - 90, cy - 35, 180, 70))

    ids = []
    for i, nd in enumerate(nodes):
        ang = math.radians(-90 + i * 360.0 / n)
        x = cx + R * math.cos(ang) - bw / 2
        y = cy + R * math.sin(ang) - bh / 2
        label = nd.get("name", f"节点{i + 1}")
        if nd.get("items"):
            label += "\n" + "；".join(nd["items"])
        cid = f"n{i + 1}"
        ids.append(cid)
        cells.append(cell(cid, label, S_BOX, x, y, bw, bh))

    feedback = spec.get("feedback_label", "反馈迭代")
    for i in range(n):
        src, dst = ids[i], ids[(i + 1) % n]
        if i == n - 1 and feedback:
            edges.append(edge("e_feedback", src, dst, S_EDGE_FEED, feedback))
        else:
            edges.append(edge(f"e_{src}_{dst}", src, dst, S_EDGE_LOOP))
    return wrap_xml("技术路线图-逻辑闭环式", 827, 1169, "\n".join(cells + edges))


GENERATORS = {"five-stage": gen_five, "loop": gen_loop,
              "three-column": lambda s: gen_columns(s),
              "five-column": lambda s: gen_columns(s, 5)}


def main():
    ap = argparse.ArgumentParser(description="学术技术路线图 mxgraph XML 生成器")
    ap.add_argument("--spec", required=True, help="spec JSON 文件路径")
    ap.add_argument("--output", required=True, help="输出 .drawio 文件路径")
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8-sig") as f:
        spec = json.load(f)
    paradigm = spec.get("paradigm", "five-stage")
    if paradigm not in GENERATORS:
        sys.exit(f"未知范式: {paradigm} (可选: {', '.join(GENERATORS)})")

    xml = GENERATORS[paradigm](spec)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(xml)

    import xml.etree.ElementTree as ET
    ET.fromstring(xml)  # 自校验: XML 良构
    n_cells = xml.count('vertex="1"') + xml.count('edge="1"')
    print(f"[OK] {paradigm} -> {args.output} ({n_cells} elements, XML valid)")


if __name__ == "__main__":
    main()
