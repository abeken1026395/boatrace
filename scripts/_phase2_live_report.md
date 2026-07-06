# Phase2 live 検証レポート

実行時刻(UTC): 2026-07-06 19:05:26

対象日: ['20260707', '20260708']

## 到達性チェック
- index(20260707): status=200 len=50897 err=-

## 探索ログ（開催場ヒットまで）
```
20260707/01:st=200,racers=6
```

## 対象: jcd=01 桐生 / hd=20260707

### 1号艇 tbody 生HTML（先頭〜4000字）
- tbody内 <tr> 数: 4
```html
<tbody class="is-fs12">
<tr>
<td class="is-boatColor1 is-fs14" rowspan="4">１</td>
<td rowspan="4"><a href="/owpc/pc/data/racersearch/profile?toban=3459"><img alt="" height="95" src="/racerphoto/3459.jpg" width="67"/></a>
</td>
<td rowspan="4">
<div class="is-fs11">3459
                            / <span class="">B1</span>
</div>
<div class="is-fs18 is-fBold"><a href="/owpc/pc/data/racersearch/profile?toban=3459">中野　　和裕</a>
</div>
<div class="is-fs11">佐賀/佐賀
                        <br/>59歳/53.0kg
                        </div>
</td>
<td class="is-lineH2" rowspan="4">F0
                        <br/>L0
                        <br/>0.17
                      </td>
<td class="is-lineH2" rowspan="4">3.44
                        <br/>12.50
                        <br/>23.75
                      </td>
<td class="is-lineH2" rowspan="4">0.00
                        <br/>0.00
                        <br/>0.00
                      </td>
<td class="is-lineH2" rowspan="4">58
                        <br/>22.92
                        <br/>36.46
                      </td>
<td class="is-lineH2" rowspan="4">70
                        <br/>30.50
                        <br/>47.52
                      </td>
<td rowspan="4"> </td>
<td class="is-boatColor5">6</td>
<td class=""> </td>
<td class="is-boatColor2">1</td>
<td class="is-boatColor6">7</td>
<td class="is-boatColor4">6</td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class="is-outColor"> </td>
<td class="is-outColor"> </td>
<td rowspan="4"><a class="number2__add2020 is-type3" href="/owpc/pc/race/racelist?rno=5&amp;jcd=01&amp;hd=20260707">5R</a></td>
</tr>
<tr>
<td class="">5</td>
<td class=""> </td>
<td class="">2</td>
<td class="">6</td>
<td class="">4</td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class="is-outColor"> </td>
<td class="is-outColor"> </td>
</tr>
<tr>
<td class="">.18</td>
<td class=""> </td>
<td class="">.24</td>
<td class="">.17</td>
<td class="">.12</td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class=""> </td>
<td class="is-outColor"> </td>
<td class="is-outColor"> </td>
</tr>
<tr class="is-fBold">
<td class=""><a href="/owpc/pc/race/raceresult?rno=6&amp;jcd=01&amp;hd=20260704">６</a></td>
<td class=""><a href="/owpc/pc/race/raceresult"></a></td>
<td class=""><a href="/owpc/pc/race/raceresult?rno=1&amp;jcd=01&amp;hd=20260705">５</a></td>
<td class=""><a href="/owpc/pc/race/raceresult?rno=7&amp;jcd=01&amp;hd=20260705">６</a></td>
<td class=""><a href="/owpc/pc/race/raceresult?rno=6&amp;jcd=01&amp;hd=20260706">６</a></td>
<td class=""><a href="/owpc/pc/race/raceresult"></a></td>
<td class=""><a href="/owpc/pc/race/raceresult"></a></td>
<td class=""><a href="/owpc/pc/race/raceresult"></a></td>
<td class=""><a href="/owpc/pc/race/raceresult"></a></td>
<td class=""><a href="/owpc/pc/race/raceresult"></a></td>
<td class=""><a href="/owpc/pc/race/raceresult"></a></td>
<td class=""><a href="/owpc/pc/race/raceresult"></a></td>
<td class="is-outColor"><a href="/owpc/pc/race/raceresult"></a></td>
<td class="is-outColor"><a href="/owpc/pc/race/raceresult"></a></td>
</tr>
</tbody>
```
- tbody直下 各<tr>のtd:
```
tr[0] (24td): ['１', '', '3459\n                            /⏎B1⏎中野\u3000\u3000和裕⏎佐賀/佐賀⏎59歳/53.0kg', 'F0⏎L0⏎0.17', '3.44⏎12.50⏎23.75', '0.00⏎0.00⏎0.00', '58⏎22.92⏎36.46', '70⏎30.50⏎47.52', '', '6', '', '1', '7', '6', '', '', '', '', '', '', '', '', '', '5R']
tr[1] (14td): ['5', '', '2', '6', '4', '', '', '', '', '', '', '', '', '']
tr[2] (14td): ['.18', '', '.24', '.17', '.12', '', '', '', '', '', '', '', '', '']
tr[3] (14td): ['６', '', '５', '６', '６', '', '', '', '', '', '', '', '', '']
```

### 今節成績ヘッダ探索
- '今節成績' を含むセル数: 0
