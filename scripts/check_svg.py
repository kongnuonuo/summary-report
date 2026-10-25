#!/usr/bin/env python3
"""内联 SVG 几何自检：文字越界 / 图形越界 / 文字重叠。

用法:
    python check_svg.py report.html

输出每个问题的定位，最后一行是 problems: N。N=0 才算通过。

为什么需要它：几何自检查不出「信息没画出来」，但能挡住最常见的两类事故——
文字跑出 viewBox（渲染后被裁掉半句话）、标注压在曲线上。目视检查接不住所有篇幅。

注意: <text transform="rotate(a cx cy)"> 必须先把四角旋转再取包围盒，
否则竖排的轴标题会被误报越界，并连带误报它与刻度重叠。
遇到误报时先确认是图错了还是检查器错了——改检查器，不要改图迁就。

依赖: 仅标准库。
"""

import math
import re
import sys
import xml.etree.ElementTree as ET

NS = "{http://www.w3.org/2000/svg}"


def main():
    if len(sys.argv) < 2:
        print("usage: python check_svg.py <file.html>")
        return 2

    html = open(sys.argv[1], encoding="utf-8").read()
    svgs = re.findall(r"<svg\b.*?</svg>", html, re.S)
    print("found %d svg" % len(svgs))

    problems = 0

    for idx, s in enumerate(svgs):
        root = ET.fromstring(s)
        vb = [float(v) for v in root.get("viewBox").split()]
        vx0, vy0, vw, vh = vb
        x_max, y_max = vx0 + vw, vy0 + vh

        def tag(e):
            return e.tag.replace(NS, "")

        boxes = []

        for e in root.iter():
            if tag(e) != "text":
                continue
            try:
                fs = float(e.get("font-size", 12))
            except ValueError:
                fs = 12.0
            txt = "".join(e.itertext())
            if not txt.strip():
                continue
            w = sum(fs * (1.0 if ord(c) > 0x2000 else 0.55) for c in txt)
            anchor = e.get("text-anchor", "start")
            try:
                x = float(e.get("x", 0))
                y = float(e.get("y", 0))
            except (TypeError, ValueError):
                continue

            if anchor == "middle":
                x0, x1 = x - w / 2, x + w / 2
            elif anchor == "end":
                x0, x1 = x - w, x
            else:
                x0, x1 = x, x + w
            y0, y1 = y - fs * 0.62, y + fs * 0.62

            tr = e.get("transform", "") or ""
            mr = re.search(r"rotate\(\s*(-?[\d.]+)[\s,]+(-?[\d.]+)[\s,]+(-?[\d.]+)", tr)
            if mr:
                ang = math.radians(float(mr.group(1)))
                rcx, rcy = float(mr.group(2)), float(mr.group(3))
                ca, sa = math.cos(ang), math.sin(ang)
                rot = []
                for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                    dx, dy = px - rcx, py - rcy
                    rot.append((dx * ca - dy * sa + rcx, dx * sa + dy * ca + rcy))
                x0 = min(p[0] for p in rot)
                x1 = max(p[0] for p in rot)
                y0 = min(p[1] for p in rot)
                y1 = max(p[1] for p in rot)

            boxes.append((x0, y0, x1, y1, txt))
            if x0 < vx0 - 0.5 or x1 > x_max + 0.5 or y0 < vy0 - 0.5 or y1 > y_max + 0.5:
                problems += 1
                print("  [TEXT-OUT] svg%d '%s' box=(%.1f,%.1f,%.1f,%.1f)"
                      % (idx, txt, x0, y0, x1, y1))

        for e in root.iter():
            t = tag(e)
            pts = []
            try:
                if t == "line":
                    pts = [(float(e.get("x1")), float(e.get("y1"))),
                           (float(e.get("x2")), float(e.get("y2")))]
                elif t == "rect":
                    x, y = float(e.get("x", 0)), float(e.get("y", 0))
                    w, hh = float(e.get("width")), float(e.get("height"))
                    pts = [(x, y), (x + w, y + hh)]
                elif t == "circle":
                    cx, cy, r = float(e.get("cx")), float(e.get("cy")), float(e.get("r"))
                    pts = [(cx - r, cy - r), (cx + r, cy + r)]
                elif t in ("path", "polyline", "polygon"):
                    d = e.get("d") or e.get("points") or ""
                    nums = [float(v) for v in re.findall(r"-?\d+\.?\d*", d)]
                    pts = list(zip(nums[0::2], nums[1::2]))
            except (TypeError, ValueError):
                continue

            for x, y in pts:
                if x < vx0 - 0.5 or x > x_max + 0.5 or y < vy0 - 0.5 or y > y_max + 0.5:
                    problems += 1
                    print("  [GEOM-OUT] svg%d <%s> point=(%.1f, %.1f)" % (idx, t, x, y))
                    break

        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if (a[0] < b[2] - 1 and b[0] < a[2] - 1
                        and a[1] < b[3] - 1 and b[1] < a[3] - 1):
                    problems += 1
                    print("  [TEXT-OVERLAP] svg%d '%s' <-> '%s'" % (idx, a[4], b[4]))

    print("problems: %d" % problems)
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
