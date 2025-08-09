# Mini Flow DSL v0 — 文法定義とサンプルフロー

## 文法定義（最小版）

```
flow <name>
  task <id>: <tool>(arg1=..., arg2=...) [retry N] [timeout 10s] [idempotency KEY]
    compensate <tool>(...)
  if <expr>
    <steps>
  end
  for <var> in <expr>
    <steps>
  end
end
```

- **flow**: フロー全体の名前
- **task**: 外部呼び出しや処理ステップ
- **if**: 条件分岐、真の場合のみ内側のステップを実行
- **for**: コレクションに対して繰り返し処理（ファンアウト）
- **end**: ブロックの終了（`if`や`for`に対応）
- オプション

  - `retry`: 再試行回数（実装側で指数バックオフ＋ジッター）
  - `timeout`: 実行のタイムアウト
  - `idempotency`: 冪等キー（同一キーなら二重実行を抑止）
  - `compensate`: 失敗時に行う逆操作（Saga パターン）

- 参照: `$taskId` または `$taskId.field`
- 式: `== != > >= < <= && || !` と `sum(), len(), abs(), hash(), fmt()` など最小限

---

## サンプルフロー：温度異常 → カメラ撮影 →LINE 通知

### イベント駆動型

```
flow temp_alert_event
  # 外部トリガで {sensor_id, temp, ts} が入ってくる
  task evt: input_event()

  if $evt.temp >= 30         # しきい値は30℃
    # 5分窓で重複抑止（同じセンサーの連投を防ぐ）
    task d: dedup(key=fmt("temp:{$evt.sensor_id}:{bucket($evt.ts,5m)}"))

    if !$d.is_new
      end
    end

    task snap: camera_capture(camera_id=$evt.sensor_id) timeout 10s retry 1
    task send: line_notify(
      message=fmt("温度アラート: {$.evt.sensor_id} {$.evt.temp}℃"),
      image_url=$snap.url
    ) retry 2 timeout 10s
      idempotency fmt("line:{hash($snap.url)}")
  end
end
```

### ポーリング型

```
flow temp_alert_poll
  task read: read_sensor(sensor_id="kitchen") timeout 5s retry 2

  if $read.temp >= 30
    task snap: camera_capture(camera_id="kitchen") timeout 10s retry 1
    task send: line_notify(
      message=fmt("温度アラート: kitchen {$read.temp}℃"),
      image_url=$snap.url
    ) retry 2 timeout 10s
      idempotency fmt("line:{hash($snap.url)}")
  end
end
```

---

### 想定ツールのインタフェース

- `input_event()` → `{sensor_id, temp, ts}`
- `dedup(key)` → `{is_new: Bool}`
- `camera_capture(camera_id)` → `{url, ts}`
- `line_notify(message, image_url)` → `{ok}`
- `read_sensor(sensor_id)` → `{temp, ts}`

### 実装上のポイント

- 異常判定のしきい値や窓幅は固定値でも引数化でもよい
- `dedup`＋`idempotency`でスパム通知を防止
- 必要に応じてヒステリシスを導入（一定温度以下まで下がるまで再通知しないなど）
