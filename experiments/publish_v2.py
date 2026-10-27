"""Build a Japanese report and an entirely local, mobile-friendly results viewer."""
import json
from pathlib import Path
from .analysis_v2 import optimal_random_reach
ROOT=Path(__file__).resolve().parents[1]
NAMES={'none':'防御なし','fixed_A':'固定A','fixed_B':'固定B','fixed_C':'固定C','fixed_D':'固定D','fixed_anchor':'固定（無作為の初期入口）','risk':'重要度優先','predictive':'前回の応答予測型','belief':'候補除外型','gated':'規則性確認型','robust':'慎重な複合型'}

def build():
    folder=ROOT/'experiments/results_v2'
    development=json.loads((folder/'development.json').read_text());holdout=json.loads((folder/'holdout.json').read_text());locked=json.loads((folder/'frozen.json').read_text())
    selected=locked['selected_policy'];rows=[r for r in holdout['rows'] if r['policy']==selected]
    strong_better=[r for r in rows if r['delta_anchor_simultaneous95'][1]<0 and r['delta_fixed_mean_simultaneous95'][1]<0]
    strong_worse=[r for r in rows if r['delta_anchor_simultaneous95'][0]>0 or r['delta_fixed_mean_simultaneous95'][0]>0]
    report='''# Mirage Shield 第2回研究：固定型の限界と、慎重な適応

2026年10月24日。第1回の結果は保存したまま、新しい実験計画・乱数・未使用条件で調査した。

## 先に結論

'''
    report+=f"採用候補は **{NAMES[selected]}**、確信度の閾値は **{locked['threshold']}**。未使用条件36組のうち、固定した入口を無作為に選ぶ方式と、固定A/B/C/Dの平均の**両方**に対して保守的な同時95%区間でも到達率が低かったのは **{len(strong_better)}組**。どちらかに対して同時区間でも悪化したのは **{len(strong_worse)}組**だった。差が確定しない組を『同等と証明』とは扱わない。\n\n"
    report+='''これは4入口・静止標的・完全な模擬応答を仮定した結果であり、実際の攻撃や生成AIへの有効性を示さない。特に同じ入口へ繰り返し進む単純な探索役では、大きな改善が出やすい。

## なぜ固定型に勝てない条件があったのか

毎回独立に一様ランダムで入口を選ぶ探索役、静止した一様標的、完全な囮1個、切替遅延なし、という条件について、標的候補の数と残り手数を状態にした動的計画法で厳密な最小到達確率を求めた。

16手の最適到達率は **74.248305318%** で、固定囮の `3/4 × (1 − (3/4)^16)` と一致する。候補数1〜4、手数0/1/2/4/16/27について分数のまま一致を自動確認した。この模型では、ランダム型に対して適応すれば必ず固定型より良くなる、という目標は成立しない。別の探索役・不完全応答・動く標的にまでこの結論を拡張してはいけない。

DPの選択肢は「標的が残っている候補の1つを守る」「候補外を守る」の2つ。候補は対称で、標的がないという正確な応答でだけ候補数が減る。過去全体を候補数へ圧縮できる条件に限定した厳密計算である。

## 新方式

- **候補除外型**：囮でない入口からempty/hintが返れば、その入口を標的候補から外し、候補確率と次回選択予測の積を使う。囮応答では候補から外さない。
- **規則性確認型**：ランダム、旧版の学習役、順番探索、4手継続の仮説を、観測された探索先の尤度で更新する。規則的探索の合計確率が閾値に達した時だけ動く。
- **慎重な複合型**：上記に加えて、学習役の仮説が十分に高い時には候補除外型の予測を使う。それ以外は元の固定入口に戻る。これは適応するかどうかも選ぶ方式で、全条件で動く方式ではない。

いずれも切替遅延が1手以上と分かっている場合は初期入口を固定する。このため遅延条件での改善は主張しない。切替時は囮が無効になる既存のコスト模型であり、配置したまま移動する設計は未実装。

empty/hintを完全な除外情報として使えるのは、この模型特有の強い仮定。囮が偽物と分かる応答も観測できる。実システムでは偽の応答や観測漏れがあるので、そのまま使える設計ではない。模型を改良候補に有利に変更したのではなく、既存の応答規則に含まれていた情報を使ったもの。

## 第1回から修正した実験設計

- 旧エンジン・旧結果・凍結ハッシュは変更していない。第2回は別ファイル・別データとして追加した。第1回の未知条件は既知として扱い、新たに条件を分けた。
- 入口名を入れ替えても動作が変わらないようにし、固定A/B/C/Dを個別に比較した。主要比較は、標的と独立に一様無作為で選ぶ初期入口を固定する方式。副比較は同一シナリオでの固定A/B/C/Dの算術平均。標的位置を見て最良入口を選ぶ『後知恵の固定方式』は使わない。
- seedの下位ビットを探索役の開始位置に直接流用せず、SHA-256で目的別seedを派生。標的、重要度、入口の並び、初期配置、探索開始位置、探索判定、選択、雑音を別系列にした。方式間では同じ世界・行動乱数を共有する。
- MT19937に加えて、SHA-256カウンタから作る別系列も検証した。暗号学的な安全性や乱数の完全独立性を主張するための比較ではない。
- seedを条件・探索役の組ごとに分離した。各組10000回を5000回ずつ2ブロックにも分けて記録。ブロック分割は完全に別の研究による追試ではない。
- 防御入力を `Public` 型に限定し、標的位置、seed、探索役の名前・内部状態、将来乱数を渡していない。重要度は全方式へ同じ情報を渡すが、使用の有無は方式による。実験器だけが正解を持つ。
- 到達率のWilson区間、同一シナリオでの対差区間に加え、検証集合全体の比較へHoeffdingの上界とunion boundを使った保守的な同時95%区間を追加。擬似乱数を独立サンプルの近似と扱う仮定に依存する。

入口名の入替ありでは物理的なAへの偏りは平均化される。そこでA/C偏重の一部条件は名前の入替を無効にし、固定入口の違いを残した。重要度連動条件でも、連動情報を利用するrisk方式を含めて全方式を公開する。

## 調整と凍結

`plan_v2.json` を作成し、開発はuniform、物理A偏重、遅い学習、切替1手遅延 × 4探索役。閾値0.6/0.8/0.95を比較し、**すべての開発セルで固定初期入口に対する悪化が1百分点以下**の候補から平均到達率が低いものを選んだ。これは観測値の選択条件であり、安全性の保証ではない。条件を満たす候補がなければ固定方式へ戻す計画だった。

エンジン、実験実行コード、計画のSHA-256と選択値を `results_v2/frozen.json` に保存してから未使用条件を実行。検証結果を見た後にエンジンや閾値を変えていない。これは今回の作業内での分離であり、第三者への事前登録や独立機関の追試ではない。検証にはC偏重、7手、27手で低探索率、2手遅延、重要度連動、名前を入れ替えた偏り、および未使用の逆順探索・途中でランダム化する探索を含めた。これは設計したストレス試験であり、現実の未知攻撃の代表サンプルではない。

| 閾値 | 開発の全セルで悪化1百分点以内 | 開発平均到達率 |
|---|---|---:|
'''
    for t in locked['trials']:report+=f"| {t['threshold']} | {'合格' if t['eligible'] else '不合格'} | {t['mean_reach']*100:.2f}% |\n"
    report+='''
## 未使用条件の全結果（採用候補）

差は「候補の到達率 − 固定初期入口の到達率」。負なら模型の防御側に有利。単位は百分点（パーセントポイント）。同時区間は固定4入口平均との比較も含めた検証全体に補正している。

| 条件 | 探索役 | 固定初期入口 | 採用候補 | 差 | 対差95%区間 | 同時95%区間 |
|---|---|---:|---:|---:|---:|---:|
'''
    for r in rows:
        fixed=next(b for b in holdout['rows'] if b['condition']==r['condition'] and b['agent']==r['agent'] and b['policy']=='fixed_anchor')
        report+=f"| {r['condition']} | {r['agent']} | {fixed['reach_rate']*100:.2f}% | {r['reach_rate']*100:.2f}% | {r['delta_anchor']*100:+.2f} | {r['delta_anchor_ci95'][0]*100:+.2f}〜{r['delta_anchor_ci95'][1]*100:+.2f} | {r['delta_anchor_simultaneous95'][0]*100:+.2f}〜{r['delta_anchor_simultaneous95'][1]*100:+.2f} |\n"
    report+='''
### 強い比較対象には負ける条件がある

C偏重の学習型では慎重な複合型70.28%、固定初期入口74.83%に対して、固定Cは29.54%だった。Cが多いという事前知識があれば固定Cの方がはるかに良い。検証結果を見て固定Cを選ぶことは公平でないが、適応型がすべての固定方式を超えたわけではないことを示す。

重要度連動の学習型でも、複合型70.00%に対して、全方式に公開された重要度を使う重要度優先型は59.54%。候補除外型は59.51%だった。複合型を選んだのは開発集合での悪化制約によるもので、各条件で最良だからではない。

ランダム型では固定初期入口に対し、差の観測値は−0.01〜+0.26百分点。改善の証明でも、悪化しない保証でもない。逆順や途中でランダム化する未使用探索役はほぼ固定と同じ動きとなり、新しい探索役全般への改善は確認できなかった。
'''
    report+='''
## 全方式の比較（未使用条件36組の単純平均）

以下の平均は選んだ条件と探索役を等しく重みづけした記述量であり、実際の攻撃頻度や期待被害の推定ではない。評価条件の作り方で変わる。早期到達で実験を止めるので、移動回数や囮応答の露出時間も方式間で違う。

| 方式 | 平均到達率 | 平均切替回数 | 到達率 + 0.01×切替回数 |
|---|---:|---:|---:|
'''
    for policy in NAMES:
        rr=[r for r in holdout['rows'] if r['policy']==policy]
        report+=f"| {NAMES[policy]} | {sum(r['reach_rate'] for r in rr)/len(rr)*100:.2f}% | {sum(r['mean_moves'] for r in rr)/len(rr):.3f} | {sum(r['cost_reach_plus_001_moves'] for r in rr)/len(rr):.4f} |\n"
    report+=f'''
合成コストの係数0.01は説明用の仮定で、現実の運用費用を表さない。主評価は到達率のまま。全政策・全条件の数値、固定4入口平均との差、2ブロック別値はJSONと結果画面で確認できる。

## 実行規模と確認

開発の閾値比較96万回、選択後の全11方式176万回、未使用条件396万回、**計668万回**。閾値比較の固定型再実行を含むので、668万個の独立シナリオではない。初期の小規模な試作計算はこの数に含めない。検証は{holdout['simultaneous_family_size']}比較へ補正し、区間半幅は{holdout['simultaneous_radius']*100:.2f}百分点。区間が広いので、数百分点程度の差について結論が出ない場合がある。

前回を含め20件のPythonテスト（厳密計算、入口名の入替、独立系列の再現、情報境界、遅延時の固定退避、結果の完全性・凍結ハッシュ・seed分離など）、旧JS/Python360ケース、前回画面/Python1680ケースの一致確認を登録。追加の画面テストでは全結果フィルタ・不利な値の表示・埋込値とJSONの一致を確認する。実機iPhone Safariの描画・操作・保存は未確認。

## 再計算

Python 3.12以上、Node.js 22以上。追加ライブラリ不要。旧結果の上書きを避け、新しい出力先へ実行する。

```
python -m experiments.evaluate_v2 --phase development --output-dir /tmp/mirage-v2-repeat
python -m experiments.evaluate_v2 --phase holdout --output-dir /tmp/mirage-v2-repeat
python -m unittest discover -s tests -v
python -m experiments.analysis_v2
python -m tests.parity_fixtures > /tmp/mirage-parity.json
node tests/legacy_parity.js
python -m tests.fair_fixtures > /tmp/mirage-fair.json
node tests/browser_smoke.js
node tests/research_dashboard.js
```

`python -m experiments.publish_v2` で保存済み結果からこのレポートと画面を再生成できる。検証ファイルや凍結済み研究を上書きする実験実行は拒否する。外部サイト、実ホスト、攻撃・スキャン機能は一切使用しない。

## まだ分からないこと

完全な候補除外が成立しない観測誤り、移動する標的、囮の見破り、複数段階のネットワーク、適応型を意識して欺く探索役は未検証。今回の検証条件を次の調整に使う時には、新しい検証集合が必要になる。慎重な複合型のモデル確率は現実の確信度として校正されていない。現段階の成果は、固定型に勝てない基本条件の説明と、模型内の特定探索パターンで改善できる候補の発見である。
'''
    (ROOT/'reports/research-v2-ja.md').write_text(report)
    data=dict(selected_policy=selected,threshold=locked['threshold'],names=NAMES,rows=holdout['rows'])
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    page='''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mirage Shield 第2回研究結果</title><style>
:root{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#081321;color:#edf5fc;line-height:1.65;padding:16px;padding-bottom:max(20px,env(safe-area-inset-bottom))}main{max-width:900px;margin:auto}h1{font-size:1.6rem}h2{font-size:1.2rem}a{color:#81efda}section,article{border:1px solid #345067;border-radius:14px;padding:16px;margin:16px 0;background:#14263a}label{display:block;margin-top:12px}select,button{font:inherit;color:inherit;background:#243d54;border:1px solid #6c8ca5;border-radius:8px;padding:10px;min-height:44px;max-width:100%}select{width:100%}button{cursor:pointer;margin:8px 8px 0 0}button:focus-visible,select:focus-visible{outline:3px solid #81efda}.metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.metrics div{padding:12px;background:#0b1a2a;border-radius:10px;overflow-wrap:anywhere}.large{display:block;font-size:1.5rem;font-weight:bold}small,.muted{color:#b3c8d8}.value{font-size:1.15rem;font-weight:bold}.good{color:#81efda}.bad{color:#ffbbb4}summary{min-height:44px;cursor:pointer}p{overflow-wrap:anywhere}@media(max-width:380px){.metrics{grid-template-columns:1fr}}
</style></head><body><main><h1>Mirage Shield：第2回研究結果</h1><p><a href="index.html">操作するシミュレーターへ</a> ／ <a href="reports/research-v2-ja.md">日本語レポート</a></p><section><strong>Pythonで実行済みの未使用条件の結果です</strong><p>各組10,000回。良い条件も悪い条件も表示します。端末上で再実行する画面ではありません。到達率は低いほど、この模型の防御側に有利です。</p><p>ランダム探索の基本条件では固定型が理論最適です。新方式の優位性を全条件や現実の攻撃に広げることはできません。</p><label for="condition">検証条件</label><select id="condition"></select><label for="agent">探索役</label><select id="agent"></select><button id="save">表示中の結果JSONを保存</button><p id="details" class="muted"></p></section><section aria-live="polite"><h2>固定方式と採用候補</h2><div id="primary" class="metrics"></div><p id="comparison"></p></section><section><h2>全方式の比較</h2><p>差は固定初期入口との比較。負なら到達が減少、正なら増加です。保守的な同時95%区間が0をまたぐ場合、差は確定できません。</p><div id="policies"></div></section><details><summary>この画面の注意点</summary><p>入口4個、静止標的、完全な囮応答という模型です。切替に遅延があれば採用候補は固定へ退避します。同率は改善の証拠ではありません。条件間の平均は現実の攻撃頻度を表しません。iPhone実機での操作確認は未実施です。</p><p><a href="experiments/results_v2/holdout.json">全結果JSON</a> ／ <a href="experiments/plan_v2.json">実験計画</a> ／ <a href="experiments/results_v2/frozen.json">調整値の凍結記録</a></p></details></main><script id="research-data" type="application/json">'''+payload+'''</script><script>
"use strict";
const data=JSON.parse(document.getElementById("research-data").textContent),$=id=>document.getElementById(id);
const conditions={unseen_C_skew_sha256:"C偏重・別乱数系列",short_horizon:"7手の短い探索",long_low_exploration:"27手・低探索率",latency_two:"囮の切替に2手かかる",importance_linked_sha256:"重要度連動・別乱数系列",randomized_labels_skew:"入口名を入れ替えた偏り"};
const agents={random:"ランダム型",learning:"学習型",sweep:"順番探索型",persistent:"4手継続型",reverse:"逆順探索型（未使用）",switching:"途中でランダムに変化（未使用）"};
for(const [id,labels] of [["condition",conditions],["agent",agents]])for(const [value,label] of Object.entries(labels)){const option=document.createElement("option");option.value=value;option.textContent=label;$(id).appendChild(option);}
$("agent").value="learning";
function currentRows(){return data.rows.filter(r=>r.condition===$("condition").value&&r.agent===$("agent").value);}
function pct(x){return (x*100).toFixed(2)+"%";}function pp(x){return (x>=0?"+":"")+(x*100).toFixed(2);}
function render(){const rows=currentRows(),base=rows.find(r=>r.policy==="fixed_anchor"),selected=rows.find(r=>r.policy===data.selected_policy);const c=selected.config;
 $("details").textContent=`各${selected.n.toLocaleString("ja-JP")}回 ／ ${c.budget}手 ／ 切替遅延${c.switch_delay}手 ／ 乱数${c.stream} ／ 調整閾値${data.threshold}`;
 $("primary").innerHTML=[base,selected].map(r=>`<div>${data.names[r.policy]}<span class="large">${pct(r.reach_rate)}</span><small>到達率95%区間 ${pct(r.ci95[0])}〜${pct(r.ci95[1])}</small></div>`).join("");
 const ci=selected.delta_anchor_simultaneous95;
 $("comparison").textContent=`固定初期入口との差 ${pp(selected.delta_anchor)}百分点。同時95%区間 ${pp(ci[0])}〜${pp(ci[1])}百分点。`+(ci[1]<0?"この条件では到達率が低下しました。":ci[0]>0?"この条件では到達率が上昇しました。":"この区間では差を確定できません。");
 $("policies").innerHTML=rows.map(r=>{const d=r.delta_anchor,ci=r.delta_anchor_simultaneous95;return `<article><h3>${data.names[r.policy]}</h3><p class="value">到達率 ${pct(r.reach_rate)}</p><p class="${d<0?'good':d>0?'bad':''}">固定初期入口との差 ${pp(d)}百分点</p><small>同時95%区間 ${pp(ci[0])}〜${pp(ci[1])}百分点<br>固定A/B/C/D平均との差 ${pp(r.delta_fixed_mean)}百分点<br>平均切替 ${r.mean_moves.toFixed(3)}回 ／ 平均使用手数 ${r.mean_turns.toFixed(2)}手</small></article>`;}).join("");
}
$("condition").onchange=render;$("agent").onchange=render;
$("save").onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({selected_policy:data.selected_policy,threshold:data.threshold,rows:currentRows()},null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download="mirage-research-v2.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
render();
</script></body></html>'''
    (ROOT/'research-v2.html').write_text(page)
    print('Built Japanese report and research-v2.html; improved on both comparators:',len(strong_better),'worse:',len(strong_worse))
if __name__=='__main__':build()
