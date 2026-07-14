import time
from pathlib import Path

import akshare as ak


DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

ASSETS = {
    "588200": "科创芯片ETF",
    "688008": "澜起科技",
}


def download_with_retry(code: str, name: str, retries: int = 3) -> None:
    """下载行情数据，失败时自动重试。"""

    for attempt in range(1, retries + 1):
        print(f"\n开始下载：{name} ({code})，第 {attempt} 次尝试")

        try:
            if code.startswith("5"):
                df = ak.fund_etf_hist_em(
                    symbol=code,
                    period="daily",
                    start_date="20240101",
                    end_date="20261231",
                    adjust="qfq",
                )
            else:
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date="20240101",
                    end_date="20261231",
                    adjust="qfq",
                )

            if df.empty:
                raise RuntimeError("接口返回了空数据")

            file_path = DATA_DIR / f"{code}.csv"
            df.to_csv(file_path, index=False, encoding="utf-8-sig")

            print("下载成功！")
            print(df.tail())
            print(f"保存位置：{file_path}")
            return

        except Exception as exc:
            print(f"本次失败：{exc}")

            if attempt < retries:
                print("等待 5 秒后重试……")
                time.sleep(5)

    print(f"{name} 连续 {retries} 次失败，稍后再试。")


def main() -> None:
    for code, name in ASSETS.items():
        download_with_retry(code, name)

    print("\n本轮任务结束。")


if __name__ == "__main__":
    main()