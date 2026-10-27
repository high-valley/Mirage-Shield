# Mirage Shield

隔離された4入口の模型による囮防御研究。外部への攻撃・スキャン機能はありません。

- [第2回研究結果の画面](research-v2.html) / [第2回の日本語レポート](reports/research-v2-ja.md)
- [第2回の計画](experiments/plan_v2.json) / [未使用条件396万回の全結果](experiments/results_v2/holdout.json)
- [日本語研究レポート](reports/research-ja.md)
- [実験計画](experiments/plan.json)
- [開発結果](experiments/results/development.json) / [未使用条件の結果](experiments/results/holdout.json)
- [旧v1.2](experiments/legacy-v1.2.html)

`index.html` をブラウザで開くと操作できます。依存ライブラリやAPIキーは不要です。GitHub Pagesはmainへレビュー・マージした後に更新されます。

Python 3.12以上、Node.js 22以上でのテスト・再計算手順は研究レポートを参照してください。予測型は条件によって固定型より悪化し、現実の防御効果を示すものではありません。

第2回は計668万回の計算を追加しました。ランダム探索の基本条件では固定型が理論最適です。慎重な複合型は一部の模型条件で改善しましたが、情報を活用する固定型や重要度優先型に負ける条件もあります。新旧結果を混同しないよう別エンジンとして保存しています。

2026年10月28日：接続停止前の第2回成果物を復旧して反映しました。さらに[観測誤りの追加試験画面](sensor-audit.html)と[日本語レポート](reports/sensor-audit-ja.md)を追加。396万回を計算し、誤り30%の学習型では複合型が固定型より悪化しました。観測の正確さへの依存が残っています。
