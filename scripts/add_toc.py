#!/usr/bin/env python3
"""给单页 HTML 报告注入左侧可折叠目录（幂等）。

用法:
    python add_toc.py report.html
    python add_toc.py report.html --width 280 --label 目录

行为:
    - 扫描全部 <h2> / <h3>，按顺序分配锚点 s1、s3-1 ……
    - 生成两级 <nav id="toc">，默认展开，点 << 收起，收起后左上角浮出 = 按钮
    - 滚动时高亮当前小节；< 900 px 视口自动收起；打印时隐藏
    - 文件里已存在 id="toc" 则直接退出，不重复注入

依赖: 仅标准库。
"""

import argparse
import re
import sys

CSS = """
body{padding-left:__W__px;transition:padding-left .26s ease}
body.toc-hidden{padding-left:0}
#toc{position:fixed;top:0;left:0;width:__W__px;height:100vh;overflow-y:auto;
     background:#F7F4EA;border-right:1px solid var(--line);padding:0 0 46px;
     font-family:Georgia,"Times New Roman",serif;font-size:13.4px;z-index:50;
     transition:transform .26s ease;scrollbar-width:thin}
#toc::-webkit-scrollbar{width:8px}
#toc::-webkit-scrollbar-thumb{background:#D8D2C2;border-radius:4px}
#toc::-webkit-scrollbar-track{background:transparent}
body.toc-hidden #toc{transform:translateX(-100%)}
.toc-head{position:sticky;top:0;display:flex;align-items:center;justify-content:space-between;
          padding:16px 14px 12px 22px;background:#F7F4EA;border-bottom:1px solid var(--line);
          font-size:12.4px;letter-spacing:.14em;color:#7A8794}
.toc-head button{border:1px solid var(--line);background:#fff;color:#7A8794;cursor:pointer;
                 width:24px;height:24px;line-height:1;border-radius:5px;font-size:13px;
                 transition:color .15s,border-color .15s}
.toc-head button:hover{color:var(--ink);border-color:var(--ink)}
#toc ul{list-style:none;margin:0;padding:0}
#toc li{margin:0}
#toc a{display:block;text-decoration:none;padding:5px 16px 5px 22px;
       border-left:3px solid transparent;line-height:1.48;color:#3C3C3C;
       transition:background .14s,color .14s,border-color .14s}
#toc a.lv2{color:var(--ink);font-weight:600;margin-top:13px}
#toc a.lv3{font-size:12.7px;color:#6B7480;padding-left:38px;padding-top:3px;padding-bottom:3px}
#toc a:hover{background:#EFEADD;color:var(--ink)}
#toc a.active{border-left-color:var(--accent);color:var(--accent);background:#F3EDDF}
#toc-fab{display:none;position:fixed;top:14px;left:14px;z-index:60;width:36px;height:36px;
         border:1px solid var(--line);background:#fff;color:var(--ink);cursor:pointer;
         border-radius:7px;font-size:15px;line-height:1;box-shadow:0 1px 3px rgba(0,0,0,.05)}
#toc-fab:hover{border-color:var(--ink)}
body.toc-hidden #toc-fab{display:block}
html{scroll-behavior:smooth}
h2,h3{scroll-margin-top:18px}
@media (max-width:900px){
  #toc{box-shadow:2px 0 14px rgba(0,0,0,.07)}
  #toc-fab{display:none}
  body.toc-hidden #toc-fab{display:block}
}
@media print{
  #toc,#toc-fab{display:none!important}
  body{padding-left:0!important}
}
"""

JS = """
<script>
(function(){
  var body=document.body, toc=document.getElementById('toc');
  var toggle=document.getElementById('toc-toggle'), fab=document.getElementById('toc-fab');
  function setHidden(v){ body.classList.toggle('toc-hidden', v); }
  if(toggle) toggle.addEventListener('click', function(){ setHidden(true); });
  if(fab) fab.addEventListener('click', function(){ setHidden(false); });
  if(window.innerWidth < 900) setHidden(true);

  var links=[].slice.call(toc.querySelectorAll('a'));
  var targets=links.map(function(a){
    return document.getElementById(a.getAttribute('href').slice(1));
  });
  function onScroll(){
    var probe=window.scrollY+140, idx=0;
    for(var i=0;i<targets.length;i++){
      var t=targets[i];
      if(t && (t.getBoundingClientRect().top + window.scrollY) <= probe) idx=i;
    }
    for(var k=0;k<links.length;k++){
      links[k].classList.toggle('active', k===idx);
    }
  }
  window.addEventListener('scroll', onScroll, {passive:true});
  window.addEventListener('resize', onScroll);
  onScroll();
})();
</script>
"""


def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", s).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--width", type=int, default=272)
    ap.add_argument("--label", default="目录")
    a = ap.parse_args()

    h = open(a.html, encoding="utf-8").read()
    if 'id="toc"' in h:
        print("跳过：文件已包含目录")
        return 0

    items = []
    state = {"h2": 0, "h3": 0}

    def repl(m):
        tag, inner = m.group(1), m.group(2)
        if tag == "h2":
            state["h2"] += 1
            state["h3"] = 0
            hid = "s%d" % state["h2"]
        else:
            state["h3"] += 1
            hid = "s%d-%d" % (state["h2"], state["h3"])
        items.append((2 if tag == "h2" else 3, hid, strip_tags(inner)))
        return '<%s id="%s">%s</%s>' % (tag, hid, inner, tag)

    h = re.sub(r"<(h2|h3)>(.*?)</\1>", repl, h, flags=re.S)

    if not items:
        print("未找到 h2/h3，放弃注入")
        return 1

    lis, i = [], 0
    while i < len(items):
        lvl, hid, txt = items[i]
        if lvl == 2:
            lis.append('<li><a class="lv2" href="#%s">%s</a>' % (hid, txt))
            subs, j = [], i + 1
            while j < len(items) and items[j][0] == 3:
                subs.append(items[j])
                j += 1
            if subs:
                lis.append("<ul>")
                for _, sh, st in subs:
                    lis.append('<li><a class="lv3" href="#%s">%s</a></li>' % (sh, st))
                lis.append("</ul>")
            lis.append("</li>")
            i = j
        else:
            i += 1

    nav = (
        '<nav id="toc" aria-label="%s">\n' % a.label
        + '<div class="toc-head"><span>%s</span>' % a.label
        + '<button id="toc-toggle" title="收起目录" aria-label="收起目录">&#171;</button></div>\n'
        + "<ul>\n" + "\n".join(lis) + "\n</ul>\n</nav>\n"
        + '<button id="toc-fab" title="展开目录" aria-label="展开目录">&#9776;</button>\n'
    )

    h = h.replace("</style>", CSS.replace("__W__", str(a.width)) + "</style>", 1)
    h = h.replace('<div class="wrap">', nav + '<div class="wrap">', 1)
    h = h.replace("</body>", JS + "</body>", 1)

    open(a.html, "w", encoding="utf-8").write(h)
    print("已注入 %d 个目录项（h2 %d / h3 %d）" % (
        len(items), sum(1 for x in items if x[0] == 2), sum(1 for x in items if x[0] == 3)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
