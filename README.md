# JavaToPython

JavaソースコードをPythonコードへ変換するCLIツール。
構文解析を用いて、クラス構造やメソッド定義の**スケルトン（骨組み）を自動生成**します。

---

## 🎯 目的

本ツールは、Javaコードを完全にPythonへ変換するものではなく、
**構造の抽出とスケルトン生成を目的**としています。

ビジネスロジック（メソッド内部処理）の変換は対象外とし、
人手による補完を前提としています。

---

## ✨ 特徴

* Javaコードからクラス・メソッド構造を抽出
* Pythonの型ヒント付きでスケルトン生成
* `javalang` による構文解析（可能な場合）
* パース失敗時のフォールバック変換あり
* CLIツールとしてシンプルに利用可能

---

## 🛠️ インストール

### 必須

* Python 3.10+

### 任意（推奨）

```bash
pip install javalang
```

※ 未インストールでも動作しますが、精度は低下します。

---

## 🚀 使い方

```bash
python JavaToPython.py <入力.java> <出力.py>
```

### 例

```bash
python JavaToPython.py Sample.java Sample.py
```

---

## 🔄 変換例

### 入力（Java）

```java
public class UserService {
    public String getName() {
        return "test";
    }
}
```

### 出力（Python）

```python
class UserService:
    """Converted from Java class UserService."""

    def getName(self) -> str:
        # TODO: メソッド本体は手で移植してください
        ...
```

---

## ⚠️ 制約

* メソッド内部のロジックは変換されません
* Java特有の構文（Stream API / ラムダ / ジェネリクスなど）は完全には対応していません
* Springなどのフレームワークには未対応です
* 完全なコード変換ではなく、あくまで補助ツールです

---

## 🧠 設計方針

本ツールは以下の考えに基づいて設計されています：

* Java → Pythonの完全自動変換は困難
* 構造変換とロジック変換は別問題
* まずは「編集しやすい骨組み」を生成することが重要

このため、あえてスコープを絞り、
**開発者の作業を効率化するツール**として設計しています。

---

## 🔮 今後の拡張

* LLM（AI）連携によるメソッド内部の自動変換
* FastAPI / Flask への自動変換
* ディレクトリ単位の一括変換
* 差分検出による再変換
* コードフォーマット（black / ruff）連携

---

## 📄 ライセンス

MIT License

---

## 👤 Author

* Koki Yoshimoto

---

## 💬 補足

このツールは「完全変換」を目指すものではなく、
**移植作業のスタート地点を作るためのツール**です。

♯♯　実行例
python JavaToPython.py examples/Sample.java output.py
