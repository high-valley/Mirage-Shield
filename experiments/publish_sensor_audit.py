"""Publish the frozen sensor stress-test without changing any policy."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def build():
    data=json.loads((ROOT/'experiments/results_sensor/audit.json').read_text())
    rows=data['rows'];chosen=data['selected_policy']
    selected=[r for r in rows if r['policy']==chosen]
    report='''# 追加研究：応答を取り違えた場合の性能

2026年10月28日。第2回で凍結した方式を変更せずに、観測の誤りに対する感度を調べた。

## 結論

一様標的・学習型で、複合型の到達率は誤りなし68.72%から誤り30%で79.96%へ悪化した。同条件の固定初期入口は74.29%で、複合型が5.67百分点悪い。重要度連動でも学習型は誤り30%で固定初期入口より5.33百分点悪い。第2回の改善が正確な観測へ依存することが分かった。現実への有効性や非劣性は示せていない。

## 試験条件

元の模型は、囮の応答を常に正しく見分けられる。今回は標的到達以外の応答を、各手で独立に0%、10%、30%の確率で「囮→空」「空・手掛かり→囮」と取り違える。探索役と防御側は同じ誤った応答を受け取る。実際の標的到達の判定と、その時点で終了する規則は正しいまま。実際の罠の接触回数と観測誤り回数は区別して集計する。

新しいseedを使い、標的の一様分布と重要度連動の2条件、6探索役、11防御方式、誤り率3段階を各10000回。計396万エピソード。独立に作った世界は12万個で、同じ世界・探索乱数・誤り乱数を方式や誤り率の間で共有する対比較である。世界ごとに複数方式を計算した396万回を、独立シナリオ数と取り違えない。

誤り系列は標的・探索系列と分離。アルゴリズムや閾値0.8は変更していない。計画、コード、前回の凍結値のハッシュを実行前に保存した。これは性能を確認する追加ストレス試験であり、この結果で候補を選び直していない。条件の一部は第2回で既知のものなので、未使用条件全般での検証とは呼ばない。

誤り率は説明用に設定した値で、実際のシステムで測定された値ではない。誤りは独立であり、意図的に誤応答を選ぶ敵対的な探索役は未検証。

## 慎重な複合型の結果

差は「複合型 − 同じ誤り条件での固定初期入口」。負なら模型の防御側に有利。対差の同時95%区間は、固定初期入口、固定4入口平均、同方式の誤りなし、という3比較を全条件に適用して補正した保守的な区間。

| 標的分布 | 探索役 | 誤り率 | 到達率 | 固定初期入口との差（百分点） | 同時95%区間 | 誤りなしからの変化（百分点） |
|---|---|---:|---:|---:|---:|---:|
'''
    for r in selected:
        lo,hi=r['delta_anchor_simultaneous95']
        report+=f"| {r['base_condition']} | {r['agent']} | {r['error_rate']*100:.0f}% | {r['reach_rate']*100:.2f}% | {r['delta_anchor']*100:+.2f} | {lo*100:+.2f}〜{hi*100:+.2f} | {r['delta_noiseless']*100:+.2f} |\n"
    report+='''
## 読み取り

'''
    for name in ('uniform','importance_linked'):
        for agent in ('learning','persistent'):
            rr=sorted([r for r in selected if r['base_condition']==name and r['agent']==agent],key=lambda r:r['error_rate'])
            report+=f"- {name} / {agent}：誤り0%→10%→30%で到達率は "+' → '.join(f"{r['reach_rate']*100:.2f}%" for r in rr)+'。\n'
    report+='\n'
    for e in (.1,.3):
        rr=[r for r in selected if r['error_rate']==e]
        worse=[r for r in rr if r['delta_noiseless_simultaneous95'][0]>0]
        worse_anchor=[r for r in rr if r['delta_anchor_simultaneous95'][0]>0]
        better_anchor=[r for r in rr if r['delta_anchor_simultaneous95'][1]<0]
        report+=f"誤り{e*100:.0f}%の12組では、誤りなしより同時区間でも到達率が上昇したのは{len(worse)}組、固定初期入口より悪化したのは{len(worse_anchor)}組、固定初期入口より改善したのは{len(better_anchor)}組。\n\n"
    report+='''応答の誤りは、候補除外の正しさと、探索役のモデル判定の両方を崩す。探索役も学習する場合には、その行動自体も変わる。このため結果は「防御側のセンサーだけの誤り」の効果ではない。誤りなしとの対差も表示したが、固定型も探索役の変化で到達率が変わりうる。

固定初期入口のランダム探索では、応答が変わっても探索先や配置が変わらないため、各誤り率で標的到達は同じになる。これを検査した。誤り率0の追加エンジンは、第2回エンジンと到達・手数・囮・切替・履歴まで一致することも確認した。

同時区間が0をまたぐことは同等性や非劣性の証明ではない。完全な候補除外と公称のモデル確率へ依存するため、今回の方式を実運用へ推奨する根拠にはならない。

## 次の改善方針

候補を一度の応答でゼロ確率にする代わりに、観測の誤りを含む確率で更新する方式が必要になる。また、モデルが外れた時に動き過ぎない退避基準と、重要度の事前情報を活用する比較方式も必要。ただし、この追加試験の結果で今の閾値を調整してから同じ条件で成功を主張することはしない。次回は開発用の誤り条件と新しい評価条件を分離する。

## 確認と再現

- Python23件（前回20件と追加3件）、旧版360ケース、前回画面1680ケースの一致確認をCIに登録。
- 全396行の結果、観測誤り回数、対差と区間を `experiments/results_sensor/audit.json` に保存。
- 凍結記録は `experiments/results_sensor/frozen.json`。計画は `experiments/plan_sensor_audit.json`。
- `python -m experiments.sensor_audit` で計算。既存の結果がある場合は上書きを拒否する。再計算はリポジトリの別コピーで結果ディレクトリを退避して実行し、元の結果を保存する。
- `python -m experiments.publish_sensor_audit` で保存済みJSONからレポート・画面を生成。
- iPhone実機Safariは未確認。画面の36フィルタと396行のデータ一致はNodeの模擬DOMで検査する。

外部サイトへの攻撃・スキャン、生成AI APIは使用しない。4入口の隔離した数値模型による研究であり、現実の攻撃防御性能を示すものではない。
'''
    (ROOT/'reports/sensor-audit-ja.md').write_text(report)
    page=(ROOT/'research-v2.html').read_text()
    old=json.loads(re.search(r'<script id="research-data" type="application/json">([\s\S]*?)</script>',page).group(1))
    payload=json.dumps(dict(selected_policy=chosen,threshold=data['threshold'],names=old['names'],rows=rows),ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    page=re.sub(r'(<script id="research-data" type="application/json">)[\s\S]*?(</script>)',lambda m:m.group(1)+payload+m.group(2),page,count=1)
    conditions={r['condition']:('一様標的' if r['base_condition']=='uniform' else '重要度連動')+f"・応答誤り{r['error_rate']*100:.0f}%" for r in rows}
    page=re.sub(r'const conditions=\{[^;]+;',lambda m:'const conditions='+json.dumps(conditions,ensure_ascii=False)+';',page,count=1)
    page=page.replace('Mirage Shield 第2回研究結果','Mirage Shield 応答誤りの追加試験').replace('Mirage Shield：第2回研究結果','Mirage Shield：応答誤りの追加試験')
    page=page.replace('reports/research-v2-ja.md','reports/sensor-audit-ja.md').replace('未使用条件の結果です','応答誤りの追加試験です')
    page=page.replace('乱数${c.stream} ／ 調整閾値${data.threshold}','乱数${c.stream} ／ 観測誤り${selected.error_rate*100}% ／ 調整閾値${data.threshold}')
    page=page.replace(' ／ 調整閾値',' ／ 固定済み閾値')
    page=page.replace('模型です。切替に遅延','模型です。探索役と防御側に同じ誤応答が届きます。切替に遅延')
    page=page.replace('experiments/results_v2/holdout.json','experiments/results_sensor/audit.json').replace('experiments/plan_v2.json','experiments/plan_sensor_audit.json').replace('experiments/results_v2/frozen.json','experiments/results_sensor/frozen.json')
    page=page.replace('<strong>Pythonで実行済みの応答誤りの追加試験です</strong>', '<strong>Pythonで実行済みの応答誤りの追加試験です</strong><p>誤り30%の学習型では、採用候補が固定型より悪化しました。下の条件を切り替えて確認できます。</p>')
    page=page.replace('mirage-research-v2.json','mirage-sensor-audit.json')
    (ROOT/'sensor-audit.html').write_text(page)
    print('Built sensor stress report and viewer')
if __name__=='__main__':build()
